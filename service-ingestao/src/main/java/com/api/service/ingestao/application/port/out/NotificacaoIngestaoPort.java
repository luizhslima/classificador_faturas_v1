package com.api.service.ingestao.application.port.out;

import com.api.service.ingestao.domain.event.ArquivoIngeridoEvent;

import reactor.core.publisher.Mono;

public interface NotificacaoIngestaoPort {
    Mono<Void> notificarNovoArquivo(ArquivoIngeridoEvent event);
}
