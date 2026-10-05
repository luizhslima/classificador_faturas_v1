package com.api.service.ingestao.application.port.out;

import com.api.service.ingestao.domain.model.ArquivoIngestao;

import reactor.core.publisher.Mono;

public interface MinioStoragePort {

    Mono<String> salvar(ArquivoIngestao arquivoFatura);
}
