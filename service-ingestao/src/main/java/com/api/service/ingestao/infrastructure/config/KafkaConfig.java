package com.api.service.ingestao.infrastructure.config;

import java.util.Map;

import org.springframework.boot.kafka.autoconfigure.KafkaProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.api.service.ingestao.domain.event.ArquivoIngeridoEvent;

import reactor.kafka.sender.KafkaSender;
import reactor.kafka.sender.SenderOptions;

@Configuration
public class KafkaConfig {
    @Bean
    public KafkaSender<String, ArquivoIngeridoEvent> reactiveKafkaSender(KafkaProperties properties) {
        Map<String, Object> props = properties.buildProducerProperties();
        SenderOptions<String, ArquivoIngeridoEvent> senderOptions = SenderOptions.create(props);

        return KafkaSender.create(senderOptions);
    }
}

