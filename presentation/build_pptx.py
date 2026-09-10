#!/usr/bin/env python3
"""
Generate kafka-as-cache.pptx from scratch, mirroring the HTML deck.

Native PowerPoint slides (editable text/shapes), dark theme to match the
web version. Diagrams are drawn with native PPTX shapes where practical.

Run:  ./.venv/bin/python build_pptx.py
Out:  kafka-as-cache.pptx  (16:9)
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ---- palette (matches the HTML) ----
BG      = RGBColor(0x0D, 0x11, 0x17)
PANEL   = RGBColor(0x16, 0x1B, 0x22)
PANEL2  = RGBColor(0x1C, 0x24, 0x30)
INK     = RGBColor(0xE6, 0xED, 0xF3)
MUTED   = RGBColor(0x91, 0x98, 0xA1)
ACCENT  = RGBColor(0x58, 0xA6, 0xFF)   # blue
GREEN   = RGBColor(0x3F, 0xB9, 0x50)
ORANGE  = RGBColor(0xF0, 0x88, 0x3E)
PINK    = RGBColor(0xDB, 0x61, 0xA2)
KAFKA   = RGBColor(0xFF, 0x9F, 0x1C)
BORDER  = RGBColor(0x30, 0x36, 0x3D)
RED     = RGBColor(0xF8, 0x51, 0x49)
GREENL  = RGBColor(0x7E, 0xE2, 0xA8)
REDL    = RGBColor(0xE6, 0xA9, 0x9A)

EMU_W, EMU_H = Inches(13.333), Inches(7.5)

prs = Presentation()
prs.slide_width = EMU_W
prs.slide_height = EMU_H
BLANK = prs.slide_layouts[6]


def slide():
    s = prs.slides.add_slide(BLANK)
    # full-bleed background
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, EMU_W, EMU_H)
    r.fill.solid(); r.fill.fore_color.rgb = BG
    r.line.fill.background()
    r.shadow.inherit = False
    # push it to back
    sp = r._element
    sp.getparent().remove(sp)
    s.shapes._spTree.insert(2, sp)
    return s


def box(s, x, y, w, h, fill=None, line=None, line_w=1.0, radius=True):
    shp = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line; shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    return shp


def text(s, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space_after=6, line_spacing=1.0):
    """runs: list of paragraphs; each paragraph is list of (txt, size, color, bold, italic)."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.line_spacing = line_spacing
        for (txt, size, color, bold, italic) in para:
            r = p.add_run(); r.text = txt
            r.font.size = Pt(size); r.font.color.rgb = color
            r.font.bold = bold; r.font.italic = italic
            r.font.name = "Segoe UI"
    return tb


def kicker(s, txt):
    text(s, 0.7, 0.55, 11, 0.4, [[(txt.upper(), 12, ACCENT, True, False)]])


def title(s, txt, color=INK):
    text(s, 0.7, 0.95, 12, 1.0, [[(txt, 34, color, True, False)]])


def R(t, sz, c, b=False, i=False):   # run helper
    return (t, sz, c, b, i)


# =================================================================
# SLIDE 1 — TITLE
# =================================================================
s = slide()
text(s, 0.7, 0.7, 8, 0.4, [[R("● Distributed Systems · Deep Dive", 12, MUTED)]])
text(s, 0.7, 1.4, 8, 0.4, [[R("APACHE KAFKA", 13, ACCENT, True)]])
text(s, 0.7, 1.95, 12, 2.2, [
    [R("Kafka as a Cache", 46, INK, True)],
    [R("A distributed key–value store, without Redis", 30, KAFKA, True)],
])
text(s, 0.7, 4.2, 11, 1.2, [[R(
    "How log compaction and Kafka Streams turn an event log into a fast, "
    "replicated, fault-tolerant key–value cache — built and dissected end to end.",
    16, MUTED)]], line_spacing=1.3)
box(s, 0.7, 5.7, 5.6, 1.0, PANEL, BORDER)
text(s, 0.9, 5.8, 5.2, 0.9, [
    [R("Spring Boot + Kafka Streams", 13, INK, True)],
    [R("KTable · RocksDB · Compacted Topics", 12, MUTED)]], space_after=2)
box(s, 6.5, 5.7, 5.6, 1.0, PANEL, BORDER)
text(s, 6.7, 5.8, 5.2, 0.9, [
    [R("Built & Verified", 13, INK, True)],
    [R("15 automated tests, incl. crash survival", 12, MUTED)]], space_after=2)


# =================================================================
# SLIDE 2 — POPULAR CACHING APPROACHES
# =================================================================
s = slide(); kicker(s, "Landscape"); title(s, "Popular ways to cache")
cards2 = [
    ("In-App (In-Memory) Cache", GREEN,
     "A map inside the app process (Caffeine, Guava, HashMap). Fastest reads — no network. But it dies with the process and each instance has its own copy.",
     "Fast · Local · Not shared · Volatile"),
    ("Distributed Cache (Redis / Memcached)", PINK,
     "A dedicated cache server all instances share over the network. Consistent, survives restarts, scales independently — but it's extra infrastructure.",
     "Shared · Network hop · Extra infra"),
    ("CDN / Edge Cache", ACCENT,
     "Caches responses near users at edge locations (CloudFront, Cloudflare). Great for static assets and read-heavy HTTP; keyed by URL, not app state.",
     "Geo-distributed · HTTP · Read-heavy"),
    ("Database / Query-Result Cache", ORANGE,
     "Caching at or in front of the DB — materialized views, query caches, read-through layers. Reduces DB load; invalidation is the hard part.",
     "Read-through · Reduces DB load · Invalidation tricky"),
]
xs = [0.7, 6.9]; ys = [1.9, 4.35]
for idx, (h, c, body, tag) in enumerate(cards2):
    x = xs[idx % 2]; y = ys[idx // 2]
    box(s, x, y, 5.7, 2.25, PANEL, BORDER)
    dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x+0.25), Inches(y+0.28), Inches(0.16), Inches(0.16))
    dot.fill.solid(); dot.fill.fore_color.rgb = c; dot.line.fill.background(); dot.shadow.inherit = False
    text(s, x+0.5, y+0.18, 5.1, 0.4, [[R(h, 16, INK, True)]])
    text(s, x+0.25, y+0.7, 5.25, 1.2, [[R(body, 12, MUTED)]], line_spacing=1.2)
    text(s, x+0.25, y+1.85, 5.25, 0.3, [[R(tag, 10.5, MUTED)]])


# =================================================================
# SLIDE 3 — WHY REDIS ISN'T ALWAYS SUITABLE
# =================================================================
s = slide(); kicker(s, "The Case Against Reaching for Redis")
title(s, "Redis is great — but not free, and not always the right fit")
cards3 = [
    ("🏗️ Operational overhead", [
        "Another system to deploy, monitor, patch and upgrade",
        "HA needs replicas + Sentinel / Cluster — real ops burden",
        "One more thing that can page you at 3am"]),
    ("💸 Cost & footprint", [
        "Redis is RAM-resident — the most expensive storage tier",
        "Managed Redis is billed per node, per hour",
        "Growing the dataset means scaling the most expensive resource (RAM)",
        "RAM is fast — but not every workload needs sub-ms reads"]),
    ("🔗 Consistency & coupling", [
        "Cache invalidation — the classic hard problem",
        "Two sources of truth (DB + cache) to keep in sync",
        "Durability is opt-in; a crash can lose recent writes",
        "Network hop + an extra failure mode"]),
]
x = 0.7
for h, items in cards3:
    box(s, x, 1.95, 3.85, 3.6, PANEL, BORDER)
    text(s, x+0.22, 2.12, 3.5, 0.5, [[R(h, 14, INK, True)]])
    paras = [[R("›  ", 12, ACCENT, True), R(it, 12, MUTED)] for it in items]
    text(s, x+0.22, 2.75, 3.5, 2.7, paras, space_after=7, line_spacing=1.1)
    x += 4.05
box(s, 0.7, 5.75, 11.9, 1.4, PANEL2, BORDER)
text(s, 0.9, 5.9, 11.5, 1.1, [[
    R("If you already run Kafka, ", 14, INK, True),
    R("a cache can ride on infrastructure you already operate, secure and pay for — "
      "no new moving part, and the data is ", 13, MUTED),
    R("durable & replicated by default.", 13, KAFKA, True)]], line_spacing=1.25)


# =================================================================
# SLIDE 4 — WHY USE KAFKA AS A DISTRIBUTED STORE
# =================================================================
s = slide(); kicker(s, "The Idea"); title(s, "Why Use Kafka as a Distributed Store?")
feats4 = [
    ("1  No new infrastructure",
     "Already using Kafka? Adding a cache means zero new systems — the store is a library running inside your app."),
    ("2  Survives node failures",
     "Kafka replicates every write across brokers. If a broker or your app crashes, nothing is lost — the cache is rebuilt from the log."),
    ("3  Scales horizontally",
     "Add more partitions and instances. Kafka Streams splits the keyspace across them — each instance owns and serves its slice."),
    ("4  History + latest value",
     "A compacted topic keeps the latest value per key, while the log still records every change. Current state AND the history behind it."),
]
xs = [0.7, 6.9]; ys = [1.95, 3.85]
for idx, (h, body) in enumerate(feats4):
    x = xs[idx % 2]; y = ys[idx // 2]
    box(s, x, y, 5.7, 1.75, PANEL, BORDER)
    text(s, x+0.25, y+0.15, 5.2, 0.4, [[R(h, 15, KAFKA, True)]])
    text(s, x+0.25, y+0.62, 5.2, 1.1, [[R(body, 12, MUTED)]], line_spacing=1.2)
# use-case strip
text(s, 0.7, 5.85, 12, 0.4, [[R("WORKS ESPECIALLY WELL FOR", 11, MUTED, True)]])
ucs = ["⚙️ Config & feature flags", "🔑 Session storage",
       "⚡ Frequently-accessed data", "🌐 Distributed app state"]
x = 0.7
for uc in ucs:
    w = 0.18 + 0.105 * len(uc)
    box(s, x, 6.25, w, 0.5, PANEL2, BORDER)
    text(s, x, 6.32, w, 0.4, [[R(uc, 12, INK)]], align=PP_ALIGN.CENTER)
    x += w + 0.2
# compact explainer
box(s, 0.7, 6.95, 11.9, 0.42, PANEL2, BORDER)
text(s, 0.9, 6.98, 11.5, 0.38, [[
    R("Compacted topic: ", 11, KAFKA, True),
    R("keeps only the latest message per key forever — e.g. (user:123,\"Alice\") then (user:123,\"Bob\") ⇒ keeps only \"Bob\".", 11, MUTED)]])


# =================================================================
# SLIDE 5 — ARCHITECTURE
# =================================================================
s = slide(); kicker(s, "How It Works")
title(s, "The architecture: two paths, one source of truth")

def node(s, x, y, w, h, fill, line, lines):
    box(s, x, y, w, h, fill, line, 1.5)
    paras = [[R(t, sz, col, bold)] for (t, sz, col, bold) in lines]
    text(s, x, y+0.12, w, h, paras, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space_after=2)

# app (write)
node(s, 0.7, 2.1, 2.4, 1.1, RGBColor(0x12,0x1D,0x2E), ACCENT,
     [("🖥️ Your App", 15, INK, True), ("producer (write)", 11, MUTED, False)])
# compacted topic
node(s, 5.0, 1.9, 3.3, 1.5, RGBColor(0x24,0x1E,0x12), KAFKA,
     [("▤ Compacted Topic", 16, KAFKA, True), ("durable · replicated log", 11, MUTED, False),
      ("◆ SOURCE OF TRUTH ◆", 11, GREEN, True), ("on the broker's disk", 10, MUTED, False)])
# kafka streams
node(s, 5.0, 3.9, 3.3, 0.95, RGBColor(0x12,0x21,0x18), GREEN,
     [("⚙️ Kafka Streams", 15, INK, True), ("consumes & materializes", 11, MUTED, False)])
# rocksdb
node(s, 5.0, 5.15, 3.3, 1.0, RGBColor(0x22,0x14,0x1E), PINK,
     [("🗄️ Local RocksDB (KTable)", 14, INK, True), ("indexed copy · in your app", 11, MUTED, False)])
# app (read)
node(s, 10.2, 5.05, 2.4, 1.1, RGBColor(0x12,0x1D,0x2E), ACCENT,
     [("🖥️ Your App", 15, INK, True), ("reader (get)", 11, MUTED, False)])

def connect(s, x1, y1, x2, y2, color):
    ln = s.shapes.add_connector(2, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    ln.line.color.rgb = color; ln.line.width = Pt(2.25)
    ln.shadow.inherit = False
    return ln
connect(s, 3.1, 2.65, 5.0, 2.65, ACCENT)        # app -> topic
text(s, 3.1, 2.25, 1.9, 0.3, [[R("send(key, value)", 10, ACCENT)]], align=PP_ALIGN.CENTER)
connect(s, 6.65, 3.4, 6.65, 3.9, GREEN)          # topic -> streams
connect(s, 6.65, 4.85, 6.65, 5.15, PINK)         # streams -> rocksdb
connect(s, 8.3, 5.6, 10.2, 5.6, PINK)            # rocksdb -> read app
text(s, 8.3, 5.2, 1.9, 0.3, [[R("local get() — no network", 9.5, PINK)]], align=PP_ALIGN.CENTER)
# write/read/gotcha mini-cards
mini = [("✏️ Write path", ACCENT, "put(key,value) produces to the topic — never writes RocksDB directly. Durable & replicated before ack."),
        ("⚡ Read path", PINK, "get(key) reads local RocksDB Streams keeps in sync — in-process, no network hop."),
        ("⏳ The gotcha", ORANGE, "producer → topic → Streams → RocksDB: not instantly readable. The eventual-consistency window.")]
x = 0.7
for h, c, body in mini:
    box(s, x, 6.35, 3.85, 0.95, PANEL, BORDER)
    # colored left edge
    e = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(6.35), Inches(0.06), Inches(0.95))
    e.fill.solid(); e.fill.fore_color.rgb = c; e.line.fill.background(); e.shadow.inherit=False
    text(s, x+0.18, 6.4, 3.6, 0.3, [[R(h, 12, INK, True)]])
    text(s, x+0.18, 6.72, 3.6, 0.55, [[R(body, 9.5, MUTED)]], line_spacing=1.05)
    x += 4.05


# =================================================================
# SLIDE 6 — CRASH INTRO
# =================================================================
s = slide(); kicker(s, "Resilience"); title(s, "What happens when things crash?")
text(s, 0.7, 1.95, 12, 1.0, [[
    R("Because the ", 15, MUTED), R("compacted topic is the source of truth", 15, KAFKA, True),
    R(" and RocksDB is only a disposable local copy, every failure recovers with ", 15, MUTED),
    R("no data loss.", 15, INK, True)]], line_spacing=1.3)
# simple flow
flow = [("🖥️ App + RocksDB", ACCENT), ("💥 crash", RED), ("▤ Topic survives ✓", KAFKA),
        ("♻️ App rebuilt", GREEN)]
x = 0.9
for i,(t,c) in enumerate(flow):
    w = 2.7
    box(s, x, 3.4, w, 1.1, PANEL, c, 1.5)
    text(s, x, 3.55, w, 0.8, [[R(t, 14, c, True)]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    if i < 3:
        text(s, x+w-0.05, 3.6, 0.6, 0.6, [[R("→", 22, MUTED, True)]], align=PP_ALIGN.CENTER)
    x += w + 0.42
text(s, 0.7, 5.0, 12, 0.5, [[R(
    "The next 5 slides walk through each scenario individually.", 13, MUTED, False, True)]])
scen = ["💥 App / pod crashes", "🗑️ RocksDB wiped", "🔀 One of many pods dies",
        "🖥️ A Kafka broker dies", "⚡ Crash mid-write"]
x = 0.7
for sc in scen:
    w = 0.2 + 0.115*len(sc)
    box(s, x, 5.7, w, 0.5, PANEL2, BORDER)
    text(s, x, 5.77, w, 0.4, [[R(sc, 12, INK)]], align=PP_ALIGN.CENTER)
    x += w + 0.2


# =================================================================
# SLIDES 7-11 — INDIVIDUAL CRASH SCENARIOS
# =================================================================
scenarios = [
    ("Crash Scenario 1 / 5", "💥 App / pod crashes",
     "The pod's in-memory state and — if its disk is ephemeral — its RocksDB files.",
     "Restart the pod. Kafka Streams re-joins, replays the topic from the last checkpoint, and rebuilds RocksDB. Data returns intact.",
     "✓ verified: hard kill -9 + restart → all keys recovered"),
    ("Crash Scenario 2 / 5", "🗑️ RocksDB wiped / lost",
     "Only the local indexed copy — e.g. the disk was cleared or the node reprovisioned.",
     "On next startup the store is rebuilt entirely from the topic. The truth was never in RocksDB — it's just a cache.",
     "✓ verified: deleted the whole state dir + restart → data fully rebuilt"),
    ("Crash Scenario 3 / 5", "🔀 One of many pods dies",
     "The partitions that pod owned become temporarily unserved.",
     "A consumer-group rebalance reassigns those partitions to surviving pods, which rebuild that slice from the log.",
     "optional standby replicas keep warm copies → near-instant failover"),
    ("Crash Scenario 4 / 5", "🖥️ A Kafka broker dies",
     "Nothing served by that broker — provided replication factor > 1.",
     "A replica on another broker is automatically promoted to leader. The topic — the source of truth — stays available.",
     "requires replication factor ≥ 2 (our local demo ran a single broker, RF 1)"),
    ("Crash Scenario 5 / 5", "⚡ Crash mid-write",
     "An unacknowledged write may or may not have landed on the broker.",
     "With acks=all a write is only 'done' once replicated. A failed send() is retried or surfaced as an error — never a silent partial state.",
     "synchronous send().get() + broker acknowledgement"),
]
for kick, ttl, lost, rec, ver in scenarios:
    s = slide(); kicker(s, kick); title(s, ttl)
    # left visual placeholder box with big icon
    box(s, 0.7, 2.1, 5.5, 4.6, PANEL, BORDER)
    text(s, 0.7, 3.5, 5.5, 1.5, [[R(ttl.split(" ",1)[0], 90, INK, True)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 0.9, 5.6, 5.1, 0.8, [[R("(animated in the HTML version)", 12, MUTED, False, True)]],
         align=PP_ALIGN.CENTER)
    # right text
    text(s, 6.6, 2.3, 6.1, 1.6, [[R("What's lost:  ", 17, REDL, True), R(lost, 17, MUTED)]], line_spacing=1.3)
    text(s, 6.6, 4.0, 6.1, 1.9, [[R("Recovery:  ", 17, GREENL, True), R(rec, 17, MUTED)]], line_spacing=1.3)
    box(s, 6.6, 6.2, 6.1, 0.7, PANEL2, BORDER)
    text(s, 6.8, 6.32, 5.8, 0.5, [[R(ver, 12.5, GREEN)]], line_spacing=1.1)


# =================================================================
# SLIDE 12 — WHY DISK IS FAST
# =================================================================
s = slide(); kicker(s, "The Obvious Objection"); title(s, "“If it's on disk, how is it fast?”")
text(s, 0.7, 1.9, 12, 0.7, [[
    R("Disk-based doesn't mean disk-speed. Both Kafka and RocksDB are engineered so the ", 14, MUTED),
    R("hot path barely touches disk", 14, KAFKA, True),
    R(" — and reads never touch the network.", 14, MUTED)]], line_spacing=1.25)
fast = [
    ("➡️ Sequential, not random", "Kafka only appends to the end of a log file. Sequential I/O is orders of magnitude faster than random seeks."),
    ("🧠 OS page cache = free RAM", "Hot data stays in the OS page cache (RAM). Reads served from memory without Kafka managing a cache itself."),
    ("💾 RocksDB hot data in memory", "RocksDB has an in-memory block cache + memtable. Hot keys answered at memory speed; only cold keys hit SSD."),
    ("🔌 No network hop on reads", "get(key) is an in-process lookup. Redis always pays a network round-trip; here the data is already on the box."),
    ("📤 Zero-copy transfer", "Kafka streams bytes straight from page cache to socket via sendfile() — skipping app copies. Little CPU per byte."),
    ("⚖️ The honest bit", "A cold key does hit disk — slower than Redis's always-RAM, but it's local SSD, not the network. Still crushes a DB query."),
]
xs = [0.7, 4.75, 8.8]; ys = [2.75, 4.65]
for idx,(h,body) in enumerate(fast):
    x = xs[idx % 3]; y = ys[idx // 3]
    fill = RGBColor(0x21,0x1C,0x12) if h.startswith("⚖️") else PANEL
    box(s, x, y, 3.85, 1.75, fill, BORDER)
    text(s, x+0.2, y+0.14, 3.5, 0.4, [[R(h, 13.5, INK, True)]])
    text(s, x+0.2, y+0.6, 3.5, 1.1, [[R(body, 11, MUTED)]], line_spacing=1.12)
text(s, 0.7, 6.65, 12, 0.6, [[
    R("Rule of thumb:  ", 13, KAFKA, True),
    R("hot data ≈ memory speed · cold data = one local disk read · reads never cross the network.", 13, MUTED)]])


# =================================================================
# SLIDE 13 — TRADE-OFFS TABLE
# =================================================================
s = slide(); kicker(s, "The Honest Verdict"); title(s, "Trade-offs: Redis vs Kafka-as-cache")
rows = [
    ("Dimension", "Redis", "Kafka-as-cache", None),
    ("Read latency", "Sub-ms, uniform (all RAM)", "Hot keys ≈ Redis (no network hop); cold = local disk", "L"),
    ("Write visibility", "Instant", "Eventually consistent (topic → Streams → RocksDB)", "L"),
    ("Random-read throughput", "Millions/sec, purpose-built", "Good, not extreme", "L"),
    ("Durability & replication", "Opt-in; can lose recent writes", "Built in — replicated log is source of truth", "R"),
    ("Rich operations", "incr, sorted sets, TTL, pub/sub", "get / put / delete only", "L"),
    ("Infrastructure", "A separate cluster to run & pay for", "None new — a library, if Kafka already runs", "R"),
    ("Crash resilience", "Restore from snapshot", "Wipe RocksDB → rebuilds from topic (verified)", "R"),
]
tx, ty = 0.7, 1.95
col_w = [3.0, 4.3, 4.6]; row_h = 0.44
for ri, (a, b, c, winner) in enumerate(rows):
    head = (ri == 0)
    x = tx
    cells = [(a, INK if head else INK), (b, INK), (c, INK)]
    for ci, (val, _col) in enumerate(cells):
        w = col_w[ci]
        fill = PANEL2 if head else PANEL
        if not head and ((winner == "L" and ci == 1) or (winner == "R" and ci == 2)):
            fill = RGBColor(0x12, 0x21, 0x18)
        box(s, x, ty + ri*row_h, w, row_h, fill, BORDER, 0.75)
        if head:
            col = INK
            if ci == 1: col = PINK
            if ci == 2: col = KAFKA
            text(s, x+0.12, ty+ri*row_h+0.04, w-0.2, row_h, [[R(val, 12, col, True)]])
        else:
            is_win = (winner == "L" and ci == 1) or (winner == "R" and ci == 2)
            col = GREENL if is_win else (INK if ci == 0 else MUTED)
            b_ = (ci == 0)
            text(s, x+0.12, ty+ri*row_h+0.05, w-0.2, row_h, [[R(val, 10.5, col, b_)]])
        x += w
by = ty + len(rows)*row_h + 0.15
box(s, 0.7, by, 5.85, 0.95, PANEL, BORDER)
text(s, 0.9, by+0.1, 5.5, 0.8, [
    [R("Reach for Redis when…", 12, PINK, True)],
    [R("pure ephemeral caching, sub-ms uniform latency, high random-read rates, rich data structures.", 10.5, MUTED)]], space_after=2, line_spacing=1.1)
box(s, 6.75, by, 5.85, 0.95, PANEL, BORDER)
text(s, 6.95, by+0.1, 5.5, 0.8, [
    [R("Reach for Kafka-as-cache when…", 12, KAFKA, True)],
    [R("you already run Kafka, want durability & replication free, tolerate a small eventual-consistency window.", 10.5, MUTED)]], space_after=2, line_spacing=1.1)
text(s, 0.7, by+1.1, 12, 0.5, [[
    R("The point was never “never Redis” — it's ", 12, MUTED),
    R("“not automatically Redis.”", 12, INK, True)]])


prs.save("kafka-as-cache.pptx")
print("wrote kafka-as-cache.pptx with", len(prs.slides.__iter__.__self__._sldIdLst), "slides")
