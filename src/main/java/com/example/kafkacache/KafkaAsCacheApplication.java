package com.example.kafkacache;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.kafka.annotation.EnableKafkaStreams;

/**
 * Application entrypoint.
 *
 * @EnableKafkaStreams tells Spring to auto-configure a Kafka Streams
 * "StreamsBuilderFactoryBean". That factory bean is what actually starts the
 * Kafka Streams runtime inside this process and wires up any KTable/KStream
 * beans we declare. Without this annotation, our topology beans would be
 * created but never started.
 */
@SpringBootApplication
@EnableKafkaStreams
public class KafkaAsCacheApplication {

    public static void main(String[] args) {
        SpringApplication.run(KafkaAsCacheApplication.class, args);
    }
}
