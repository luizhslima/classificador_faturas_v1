package com.api.service.ingestao.infrastructure.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.api.service.ingestao.application.port.in.PublicarArquivoUseCase;
import com.api.service.ingestao.application.usecase.IngerirArquivoBronzeUseCaseImpl;

@Configuration
public class UseCaseConfig {

    @Bean
    public PublicarArquivoUseCase publicarArquivoUseCase(
            com.api.service.ingestao.application.port.out.NotificacaoIngestaoPort notificacaoIngestaoPort,
            com.api.service.ingestao.application.port.out.MinioStoragePort minioStoragePort) {
        return new IngerirArquivoBronzeUseCaseImpl(notificacaoIngestaoPort,
                minioStoragePort);
    }
}
