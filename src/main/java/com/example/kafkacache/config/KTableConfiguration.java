package com.example.kafkacache.config;

import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.KTable;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.state.KeyValueStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Defines the Kafka Streams topology: read the compacted topic AS A TABLE and
 * materialize it into a named, queryable local state store (backed by RocksDB).
 *
 * This is the "Step 4" from the mental model:
 *   compacted topic (the log)  ->  KTable / RocksDB (indexed table)
 *
 * `streamsBuilder.table(...)` (as opposed to `.stream(...)`) is what interprets
 * each record as an UPSERT into a table:
 *   (key, value)  -> put(key, value)
 *   (key, null)   -> delete(key)      <-- tombstone semantics, for free
 *
 * `Materialized.as(storeName)` gives the store a name so we can look it up later
 * via interactive queries (that's how the read path in the service works).
 */
@Configuration
public class KTableConfiguration {

    private final String topicName;
    private final String storeName;

    public KTableConfiguration(
            @Value("${distributed-store.topic-name}") String topicName,
            @Value("${distributed-store.store-name}") String storeName) {
        this.topicName = topicName;
        this.storeName = storeName;
    }

    /**
     * Spring Kafka injects the shared {@link StreamsBuilder} (created because of
     * @EnableKafkaStreams). We declare our topology against it; Spring then
     * builds and starts the Streams runtime once all such beans are registered.
     */
    @Bean
    public KTable<String, String> keyValueTable(StreamsBuilder streamsBuilder) {
        return streamsBuilder.table(
                topicName,
                // How to read records off the topic (key + value are Strings).
                Consumed.with(Serdes.String(), Serdes.String()),
                // How to store them locally, and under what queryable name.
                Materialized.<String, String, KeyValueStore<Bytes, byte[]>>as(storeName)
                        .withKeySerde(Serdes.String())
                        .withValueSerde(Serdes.String())
        );
    }
}
