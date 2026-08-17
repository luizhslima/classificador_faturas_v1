package com.api.service.ingestao.application.usecase;

import com.api.service.ingestao.application.port.in.PublicarArquivoUseCase;

import java.time.Instant;

import com.api.service.ingestao.application.port.in.PublicarArquivoCommand;
import com.api.service.ingestao.application.port.out.MinioStoragePort;
import com.api.service.ingestao.application.port.out.NotificacaoIngestaoPort;
import com.api.service.ingestao.domain.event.ArquivoIngeridoEvent;
import com.api.service.ingestao.domain.model.ArquivoIngestao;

import reactor.core.publisher.Mono;

public class IngerirArquivoBronzeUseCaseImpl implements PublicarArquivoUseCase {

    private final NotificacaoIngestaoPort notificacaoIngestaoPort;
    private final MinioStoragePort minioStoragePort;

    public IngerirArquivoBronzeUseCaseImpl(NotificacaoIngestaoPort notificacaoIngestaoPort,
            MinioStoragePort minioStoragePort) {
        this.notificacaoIngestaoPort = notificacaoIngestaoPort;
        this.minioStoragePort = minioStoragePort;
    }

    @Override
    public Mono<String> executar(PublicarArquivoCommand command) {
        // Implementação do método para criar o arquivo no Data Lake
        ArquivoIngestao arquivoIngestao = new ArquivoIngestao(
                command.nomeArquivo(),
                command.conteudo(),
                command.sourceContext());
        return this.minioStoragePort.salvar(arquivoIngestao)
                .flatMap(caminhoSalvo -> {
                    var event = new ArquivoIngeridoEvent(
                            arquivoIngestao.getId(),
                            arquivoIngestao.getContext(),
                            caminhoSalvo,
                            Instant.now().toEpochMilli());
                    return this.notificacaoIngestaoPort.notificarNovoArquivo(event).thenReturn(caminhoSalvo);
                });
    }

}
