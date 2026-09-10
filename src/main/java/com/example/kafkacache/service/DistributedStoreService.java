package com.example.kafkacache.service;

import com.example.kafkacache.model.StoredValue;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StoreQueryParameters;
import org.apache.kafka.streams.state.KeyValueIterator;
import org.apache.kafka.streams.state.QueryableStoreTypes;
import org.apache.kafka.streams.state.ReadOnlyKeyValueStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.config.StreamsBuilderFactoryBean;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

/**
 * The core key-value operations. This class makes the two-path design explicit:
 *
 *   WRITE PATH  (put/delete): produce a record to the compacted topic via
 *               KafkaTemplate. We do NOT write to the local store directly.
 *
 *   READ PATH   (get/getAll): query the local materialized state store that
 *               Kafka Streams keeps in sync from the topic.
 *
 * The gap between "write landed in the topic" and "write visible in the local
 * store" is exactly the eventual-consistency window the article warns about.
 */
@Service
public class DistributedStoreService {

    private static final Logger log = LoggerFactory.getLogger(DistributedStoreService.class);

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final StreamsBuilderFactoryBean streamsBuilderFactoryBean;
    private final ObjectMapper objectMapper;
    private final String topicName;
    private final String storeName;

    public DistributedStoreService(
            KafkaTemplate<String, String> kafkaTemplate,
            StreamsBuilderFactoryBean streamsBuilderFactoryBean,
            ObjectMapper objectMapper,
            @Value("${distributed-store.topic-name}") String topicName,
            @Value("${distributed-store.store-name}") String storeName) {
        this.kafkaTemplate = kafkaTemplate;
        this.streamsBuilderFactoryBean = streamsBuilderFactoryBean;
        this.objectMapper = objectMapper;
        this.topicName = topicName;
        this.storeName = storeName;
    }

    // ---------------------------------------------------------------- WRITE

    /**
     * Store (create or overwrite) a value.
     *
     * We send (key, jsonValue) to the compacted topic. Kafka guarantees all
     * records with the same key go to the same partition, so the key's history
     * — and therefore compaction — stays consistent. We block on the send so
     * the caller knows the write is durably acknowledged by the broker.
     */
    public StoredValue put(String key, String value) {
        StoredValue stored = StoredValue.create(key, value);
        try {
            String json = objectMapper.writeValueAsString(stored);
            // .get() makes this synchronous: wait for the broker ack.
            kafkaTemplate.send(topicName, key, json).get(5, TimeUnit.SECONDS);
            log.info("PUT key='{}' -> produced to topic (not yet necessarily in local store)", key);
            return stored;
        } catch (Exception e) {
            throw new RuntimeException("Failed to store key=" + key, e);
        }
    }

    /**
     * Delete a key by producing a TOMBSTONE: a record with a null value.
     *
     * A null value is Kafka's delete marker. The KTable interprets (key, null)
     * as "remove key", and log compaction eventually physically purges both the
     * old values and the tombstone itself. This is how deletes work in a
     * compacted-topic key-value store — there is no separate "delete" command.
     */
    public boolean delete(String key) {
        try {
            kafkaTemplate.send(topicName, key, null).get(5, TimeUnit.SECONDS);
            log.info("DELETE key='{}' -> tombstone (null value) produced", key);
            return true;
        } catch (Exception e) {
            throw new RuntimeException("Failed to delete key=" + key, e);
        }
    }

    // ----------------------------------------------------------------- READ

    /** Point lookup against the local state store. */
    public Optional<StoredValue> get(String key) {
        String json = store().get(key);
        if (json == null) {
            return Optional.empty();
        }
        return Optional.of(deserialize(json));
    }

    /** Full scan of the local state store (fine for a demo; O(n)). */
    public List<StoredValue> getAll() {
        List<StoredValue> result = new ArrayList<>();
        try (KeyValueIterator<String, String> it = store().all()) {
            while (it.hasNext()) {
                result.add(deserialize(it.next().value));
            }
        }
        return result;
    }

    // -------------------------------------------------------------- HELPERS

    /**
     * Obtain a queryable handle to the materialized state store.
     *
     * On startup (or after a rebalance) the store may not be queryable yet:
     * Kafka Streams has to move to RUNNING and restore state from the topic
     * first. Querying too early throws, so we retry briefly. This is the
     * "handling state store availability" concern from the article.
     */
    private ReadOnlyKeyValueStore<String, String> store() {
        KafkaStreams streams = streamsBuilderFactoryBean.getKafkaStreams();
        if (streams == null) {
            throw new IllegalStateException("Kafka Streams is not initialized yet");
        }

        int retries = 20;
        while (true) {
            try {
                return streams.store(
                        StoreQueryParameters.fromNameAndType(
                                storeName, QueryableStoreTypes.keyValueStore()));
            } catch (Exception e) {
                if (--retries <= 0) {
                    throw new IllegalStateException(
                            "State store '" + storeName + "' not available (Streams state: "
                                    + streams.state() + ")", e);
                }
                try {
                    Thread.sleep(250);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    throw new IllegalStateException("Interrupted waiting for store", ie);
                }
            }
        }
    }

    private StoredValue deserialize(String json) {
        try {
            return objectMapper.readValue(json, StoredValue.class);
        } catch (Exception e) {
            throw new RuntimeException("Failed to deserialize stored value: " + json, e);
        }
    }
}
