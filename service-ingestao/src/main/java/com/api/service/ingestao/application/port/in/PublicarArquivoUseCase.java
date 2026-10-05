package com.api.service.ingestao.application.port.in;

import reactor.core.publisher.Mono;

public interface PublicarArquivoUseCase {
    Mono<String> executar(PublicarArquivoCommand command);
}
