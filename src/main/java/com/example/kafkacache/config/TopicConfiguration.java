package com.example.kafkacache.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.common.config.TopicConfig;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

import java.util.Map;

/**
 * Declares the compacted topic that backs our key-value store.
 *
 * Any {@link NewTopic} bean is picked up by Spring Kafka's KafkaAdmin and
 * created on the broker at startup if it doesn't already exist. (It will NOT
 * change the config of an existing topic — that's an idempotent "create if
 * absent".)
 *
 * The single most important line here is the cleanup policy: COMPACT. That is
 * what tells Kafka "keep the latest value per key forever" instead of the
 * default "delete messages older than the retention window". Compaction is the
 * mechanism that gives us key-value semantics on top of an append-only log.
 */
@Configuration
public class TopicConfiguration {

    private final String topicName;

    public TopicConfiguration(@Value("${distributed-store.topic-name}") String topicName) {
        this.topicName = topicName;
    }

    @Bean
    public NewTopic distributedStoreTopic() {
        return TopicBuilder.name(topicName)
                // More partitions = more parallelism across app instances.
                // Each key is hashed to exactly one partition, so a key's whole
                // history lives in one partition (required for correct compaction).
                .partitions(6)
                // Single broker in this setup, so replicas must be 1.
                .replicas(1)
                .configs(Map.of(
                        // THE key setting: compact instead of delete.
                        TopicConfig.CLEANUP_POLICY_CONFIG, TopicConfig.CLEANUP_POLICY_COMPACT,

                        // The next three just make compaction run AGGRESSIVELY so
                        // we can SEE it during a short demo. In production you'd
                        // leave these at defaults (compaction would lag by minutes/hours).

                        // Compact once even 1% of the log is "dirty" (has overwrites).
                        TopicConfig.MIN_CLEANABLE_DIRTY_RATIO_CONFIG, "0.01",
                        // Roll a new log segment every 100ms. Compaction only acts on
                        // CLOSED segments, so tiny segments = near-immediate compaction.
                        TopicConfig.SEGMENT_MS_CONFIG, "100",
                        // Don't force a delay before a record becomes compactable.
                        TopicConfig.MIN_COMPACTION_LAG_MS_CONFIG, "0",
                        // How long a tombstone (null value = delete marker) is retained
                        // before compaction is allowed to purge it. Short, so deletes
                        // fully disappear quickly in the demo.
                        TopicConfig.DELETE_RETENTION_MS_CONFIG, "100"
                ))
                .build();
    }
}
