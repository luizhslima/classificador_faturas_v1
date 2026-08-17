package com.api.service.ingestao.adapter.out.storage;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import com.api.service.ingestao.application.port.out.MinioStoragePort;
import com.api.service.ingestao.domain.model.ArquivoIngestao;

import reactor.core.publisher.Mono;
import software.amazon.awssdk.core.async.AsyncRequestBody;
import software.amazon.awssdk.services.s3.S3AsyncClient;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;

@Component
public class MinioDatalakeAdapter implements MinioStoragePort {

    private final S3AsyncClient minioClient;
    private final String bucketName;

    public MinioDatalakeAdapter(S3AsyncClient minioClient,
            @Value("${datalake.minio.bucket-name:bronze-raw}") String bucketName) {
        this.minioClient = minioClient;
        this.bucketName = bucketName;
    }

    @Override
    public Mono<String> salvar(ArquivoIngestao arquivoFatura) {
        PutObjectRequest request = PutObjectRequest.builder()
                .bucket(bucketName)
                .key(arquivoFatura.gerarCaminhoBronze())
                .metadata(arquivoFatura.getMetadados())
                .contentType(arquivoFatura.getContentType())
                .build();
                
        return Mono
                .fromFuture(
                        () -> minioClient.putObject(request, AsyncRequestBody.fromBytes(arquivoFatura.getConteudo())))
                .doOnSuccess(
                        response -> System.out.println("Arquivo salvo no MinIO: " + arquivoFatura.gerarCaminhoBronze()))
                .thenReturn(arquivoFatura.gerarCaminhoBronze());
    }

}
