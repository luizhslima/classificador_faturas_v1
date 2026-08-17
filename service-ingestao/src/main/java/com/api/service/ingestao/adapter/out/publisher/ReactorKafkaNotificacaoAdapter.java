package com.api.service.ingestao.adapter.out.publisher;

import org.apache.kafka.clients.producer.ProducerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import com.api.service.ingestao.application.port.out.NotificacaoIngestaoPort;
import com.api.service.ingestao.domain.event.ArquivoIngeridoEvent;

import reactor.core.publisher.Mono;
import reactor.kafka.sender.KafkaSender;
import reactor.kafka.sender.SenderRecord;

@Component
public class ReactorKafkaNotificacaoAdapter implements NotificacaoIngestaoPort {


    private static final Logger log = LoggerFactory.getLogger(ReactorKafkaNotificacaoAdapter.class);
    private static final String TOPICO_INGESTAO = "datalake-bronze-ingestao-topic";

    private final KafkaSender<String, ArquivoIngeridoEvent> sender;

    public ReactorKafkaNotificacaoAdapter(KafkaSender<String, ArquivoIngeridoEvent> sender) {
        this.sender = sender;
    }

    @Override
    public Mono<Void> notificarNovoArquivo(ArquivoIngeridoEvent evento) {
        ProducerRecord<String, ArquivoIngeridoEvent> producerRecord = 
                new ProducerRecord<>(TOPICO_INGESTAO, evento.idArquivo(), evento);

        // 2. O SenderRecord envelopa o ProducerRecord com um Metadado de Correlação.
        // Isso permite rastrear o sucesso/falha de forma assíncrona sem bloquear threads.
        SenderRecord<String, ArquivoIngeridoEvent, String> senderRecord = 
                SenderRecord.create(producerRecord, evento.idArquivo());

        // 3. Envia o evento de forma reativa
        return sender.send(Mono.just(senderRecord))
                .doOnNext(result -> {
                    // O ACK do Kafka voltou com sucesso
                    var metadata = result.recordMetadata();
                    log.info("Notificação enviada aos workers! | ID: {} | Tópico: {} | Partição: {} | Offset: {}",
                            result.correlationMetadata(),
                            metadata.topic(),
                            metadata.partition(),
                            metadata.offset());
                })
                .doOnError(e -> log.error("FALHA CRÍTICA: Arquivo {} salvo no MinIO, mas falha ao notificar Kafka.", evento.idArquivo(), e))
                // 4. Converte o SenderResult em Mono<Void>, honrando o contrato da Porta
                .then();
    }

}
