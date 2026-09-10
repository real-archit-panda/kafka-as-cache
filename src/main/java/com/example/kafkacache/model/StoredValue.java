package com.example.kafkacache.model;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.Instant;

/**
 * The value we actually store in the topic, serialized as JSON.
 *
 * We could store the raw string directly, but wrapping it lets us carry a bit
 * of metadata — when it was created/updated and a monotonic version stamp —
 * which is typical of a real cache entry and makes the demo output more
 * informative.
 *
 * A Java record gives us an immutable, boilerplate-free carrier. Jackson can
 * serialize/deserialize records out of the box (Spring Boot ships a recent
 * Jackson that supports this).
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record StoredValue(
        String key,
        String value,
        Instant createdAt,
        Instant updatedAt,
        long version
) {
    /** Factory for a brand-new entry (created == updated). */
    public static StoredValue create(String key, String value) {
        Instant now = Instant.now();
        return new StoredValue(key, value, now, now, System.currentTimeMillis());
    }

    /** Returns a copy representing an update, preserving the original createdAt. */
    public StoredValue withUpdatedValue(String newValue) {
        return new StoredValue(
                key,
                newValue,
                createdAt,
                Instant.now(),
                System.currentTimeMillis()
        );
    }
}
