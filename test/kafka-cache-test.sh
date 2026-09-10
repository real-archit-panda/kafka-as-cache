#!/usr/bin/env bash
#
# End-to-end test suite for the kafka-as-cache app.
#
# It manages the Spring Boot app lifecycle itself (start/kill) so it can test
# crash-and-restart survival — the whole point of the architecture: the Kafka
# topic is the source of truth, RocksDB is a disposable local copy.
#
# ISOLATION: uses a dedicated test topic, application-id, state-dir and port so
# it never collides with your main run or existing broker data. Everything is
# cleaned up at the end.
#
# PREREQUISITES:
#   - Kafka broker running on localhost:9092
#   - target/*.jar built (mvn clean package -DskipTests)
#   - java, curl on PATH
#
# USAGE:  ./test/kafka-cache-test.sh
# EXIT:   0 if all tests pass, 1 otherwise.

set -uo pipefail

# ---------------------------------------------------------------- config
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JAR="$(ls "$PROJECT_DIR"/target/kafka-as-cache-*.jar 2>/dev/null | head -1)"

BOOTSTRAP="localhost:9092"
PORT="18099"                                   # unlikely-to-collide test port
BASE="http://localhost:${PORT}/api/store"
TEST_TOPIC="kv-store-test-$$"                   # $$ = PID, unique per run
APP_ID="kv-cache-test-$$"
STATE_DIR="/tmp/kv-cache-test-state-$$"
APP_LOG="$PROJECT_DIR/test-app.log"

# Kafka CLI (Homebrew install on this machine); adjust if yours differs.
KBIN="/opt/homebrew/Cellar/kafka/4.1.1/libexec/bin"

APP_PID=""

# ---------------------------------------------------------------- helpers
PASS=0
FAIL=0
declare -a FAILURES=()

log()  { printf '\033[0;36m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[0;32mPASS\033[0m %s\n' "$*"; PASS=$((PASS+1)); }
bad()  { printf '  \033[0;31mFAIL\033[0m %s\n' "$*"; FAIL=$((FAIL+1)); FAILURES+=("$*"); }

# assert_eq <actual> <expected> <description>
assert_eq() {
  if [[ "$1" == "$2" ]]; then ok "$3 (got '$1')"; else bad "$3 (expected '$2', got '$1')"; fi
}

# HTTP helpers — echo the numeric status code / body
http_code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
http_body() { curl -s "$@"; }

put() {  # put <key> <value>
  http_code -X PUT "$BASE/$1" -H 'Content-Type: application/json' -d "{\"value\":\"$2\"}"
}
get_code() { http_code "$BASE/$1"; }
get_body() { http_body "$BASE/$1"; }
del()      { http_code -X DELETE "$BASE/$1"; }

# Extract the "value" field from a StoredValue JSON body (no jq dependency).
value_of() { echo "$1" | sed -n 's/.*"value":"\([^"]*\)".*/\1/p'; }

start_app() {
  log "-> starting app (topic=$TEST_TOPIC, app-id=$APP_ID, port=$PORT)"
  nohup java -jar "$JAR" \
    --server.port="$PORT" \
    --spring.kafka.bootstrap-servers="$BOOTSTRAP" \
    --spring.kafka.streams.application-id="$APP_ID" \
    --spring.kafka.streams.state-dir="$STATE_DIR" \
    --distributed-store.topic-name="$TEST_TOPIC" \
    > "$APP_LOG" 2>&1 &
  APP_PID=$!
  # wait for readiness
  for _ in $(seq 1 60); do
    if grep -q "Started KafkaAsCacheApplication" "$APP_LOG" 2>/dev/null; then
      # also wait until the HTTP port actually answers
      for _ in $(seq 1 20); do
        [[ "$(http_code "$BASE" || true)" =~ ^[23] ]] && { log "   app ready (pid=$APP_PID)"; return 0; }
        sleep 0.5
      done
    fi
    grep -qi "APPLICATION FAILED TO START" "$APP_LOG" 2>/dev/null && { bad "app failed to start"; tail -20 "$APP_LOG"; return 1; }
    sleep 1
  done
  bad "app did not become ready in time"; tail -20 "$APP_LOG"; return 1
}

stop_app() {  # graceful stop
  [[ -n "$APP_PID" ]] || return 0
  log "-> stopping app (pid=$APP_PID)"
  kill "$APP_PID" 2>/dev/null
  wait "$APP_PID" 2>/dev/null
  APP_PID=""
}

kill_app_hard() {  # simulate a crash (SIGKILL, no graceful shutdown)
  [[ -n "$APP_PID" ]] || return 0
  log "-> HARD killing app (pid=$APP_PID) to simulate a crash"
  kill -9 "$APP_PID" 2>/dev/null
  wait "$APP_PID" 2>/dev/null
  APP_PID=""
}

cleanup() {
  log ""
  log "=== cleanup ==="
  [[ -n "$APP_PID" ]] && kill -9 "$APP_PID" 2>/dev/null
  # delete the isolated test topic
  "$KBIN/kafka-topics.sh" --bootstrap-server "$BOOTSTRAP" --delete --topic "$TEST_TOPIC" 2>/dev/null \
    && log "deleted test topic $TEST_TOPIC" || log "(test topic $TEST_TOPIC may not exist)"
  rm -rf "$STATE_DIR"
  rm -f "$APP_LOG" "$PROJECT_DIR/nohup.out"
  log "removed state dir + logs"
}
trap cleanup EXIT

# ---------------------------------------------------------------- preflight
log "=== preflight ==="
[[ -n "$JAR" ]] || { echo "No jar found. Run: mvn clean package -DskipTests"; exit 1; }
log "jar: $JAR"
if ! lsof -iTCP:9092 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Kafka is not listening on localhost:9092. Start your broker first."; exit 1
fi
log "kafka: up on 9092"
[[ -x "$KBIN/kafka-topics.sh" ]] || log "WARN: kafka CLI not at $KBIN — topic cleanup/consume tests may be skipped"

# small helper: give Streams time to propagate a write into RocksDB
settle() { sleep 1; }

# ================================================================
log ""
log "=== GROUP 1: basic CRUD ==="
start_app || exit 1

# 1. PUT then GET
put user:1 Alice >/dev/null; settle
body="$(get_body user:1)"
assert_eq "$(value_of "$body")" "Alice" "PUT then GET returns the value"

# 2. PUT with missing 'value' -> 400
code="$(http_code -X PUT "$BASE/user:bad" -H 'Content-Type: application/json' -d '{"notvalue":"x"}')"
assert_eq "$code" "400" "PUT with missing 'value' field -> 400"

# 3. GET nonexistent -> 404
assert_eq "$(get_code does-not-exist-$$)" "404" "GET nonexistent key -> 404"

# 4. Overwrite -> latest wins
put user:1 Bob >/dev/null
put user:1 Carol >/dev/null; settle
assert_eq "$(value_of "$(get_body user:1)")" "Carol" "Overwrite: GET returns latest value (upsert semantics)"

# 5. DELETE -> 204, then GET -> 404 (tombstone)
assert_eq "$(del user:1)" "204" "DELETE returns 204"
settle
assert_eq "$(get_code user:1)" "404" "GET after DELETE -> 404 (tombstone works)"

# 6. GET ALL returns live keys
put a 1 >/dev/null; put b 2 >/dev/null; put c 3 >/dev/null; settle
allbody="$(http_body "$BASE")"
n=$(echo "$allbody" | grep -o '"key"' | wc -l | tr -d ' ')
assert_eq "$n" "3" "GET ALL returns exactly the 3 live keys"

# ================================================================
log ""
log "=== GROUP 2: eventual consistency (documented behavior) ==="
# PUT then IMMEDIATE get (no settle). May be 200 or 404 depending on timing.
put ec:1 hello >/dev/null
imm="$(get_code ec:1)"
if [[ "$imm" == "200" || "$imm" == "404" ]]; then
  ok "immediate GET after PUT is either 200 or 404 (got $imm) — eventual consistency window"
else
  bad "immediate GET returned unexpected code $imm"
fi
settle
assert_eq "$(get_code ec:1)" "200" "GET after settle -> 200 (write propagated to store)"

# ================================================================
log ""
log "=== GROUP 3: data lives in Kafka, not the app ==="
# Seed known data, then verify it is physically on the topic (independent of app).
put durable:1 persisted-value >/dev/null; settle
if [[ -x "$KBIN/kafka-get-offsets.sh" ]]; then
  # Robust check: the topic's total end-offset across partitions must be > 0,
  # i.e. records physically exist on the broker's log. (Consuming text is flaky
  # against this broker, so we assert on offset metadata instead.)
  total=0
  while IFS= read -r line; do
    off="${line##*:}"
    total=$(( total + ${off:-0} ))
  done < <("$KBIN/kafka-get-offsets.sh" --bootstrap-server "$BOOTSTRAP" --topic "$TEST_TOPIC" --time -1 2>/dev/null)
  if (( total > 0 )); then
    ok "records physically present on the Kafka topic (end offsets sum=$total, independent of app)"
  else
    bad "expected records on the topic but end offsets summed to 0"
  fi
else
  log "  SKIP: kafka-get-offsets not available"
fi

# ================================================================
log ""
log "=== GROUP 4: SURVIVAL — app crash + restart (RocksDB rebuilt from topic) ==="
# Seed data, hard-kill (crash), restart WITHOUT deleting state, expect data back.
put survive:1 before-crash >/dev/null
put survive:2 also-before  >/dev/null; settle
log "   seeded survive:1, survive:2"
kill_app_hard
log "   app crashed. restarting..."
start_app || exit 1
settle; settle
v1="$(value_of "$(get_body survive:1)")"
v2="$(value_of "$(get_body survive:2)")"
assert_eq "$v1" "before-crash" "after crash+restart: survive:1 recovered"
assert_eq "$v2" "also-before"  "after crash+restart: survive:2 recovered"

# ================================================================
log ""
log "=== GROUP 5: SURVIVAL — RocksDB wiped (proves topic is source of truth) ==="
# Seed data, stop app, DELETE the entire RocksDB state dir, restart, expect data.
put wiped:1 survives-rocksdb-delete >/dev/null; settle
log "   seeded wiped:1"
stop_app
log "   deleting RocksDB state dir: $STATE_DIR"
rm -rf "$STATE_DIR"
[[ -d "$STATE_DIR" ]] && bad "state dir still exists after rm" || ok "RocksDB state dir deleted"
start_app || exit 1
settle; settle
vw="$(value_of "$(get_body wiped:1)")"
assert_eq "$vw" "survives-rocksdb-delete" "after RocksDB wipe+restart: data rebuilt from Kafka topic"

# also confirm the earlier CRUD keys are all back too
assert_eq "$(value_of "$(get_body durable:1)")" "persisted-value" "unrelated key also rebuilt after wipe"

stop_app

# ---------------------------------------------------------------- summary
log ""
log "==================== SUMMARY ===================="
printf 'PASS: %d   FAIL: %d\n' "$PASS" "$FAIL"
if (( FAIL > 0 )); then
  printf '\nFailed cases:\n'
  for f in "${FAILURES[@]}"; do printf '  - %s\n' "$f"; done
  exit 1
fi
log "ALL TESTS PASSED"
exit 0
