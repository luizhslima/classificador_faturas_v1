package com.api.service.ingestao.adapter.in.web;

import org.springframework.http.HttpStatus;
import org.springframework.core.io.buffer.DataBufferUtils;
import org.springframework.http.codec.multipart.FilePart;
import org.springframework.http.codec.multipart.FormFieldPart;
import org.springframework.http.codec.multipart.Part;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.server.ServerRequest;
import org.springframework.web.reactive.function.server.ServerResponse;

import java.net.URI;
import java.util.Map;

import com.api.service.ingestao.application.port.in.PublicarArquivoCommand;
import com.api.service.ingestao.application.port.in.PublicarArquivoUseCase;
import com.api.service.ingestao.domain.model.types.SourceContext;

import reactor.core.publisher.Mono;

@Component
public class ArquivoHandler {
    public final PublicarArquivoUseCase publicarArquivoUseCase;

    public ArquivoHandler(PublicarArquivoUseCase publicarArquivoUseCase) {
        this.publicarArquivoUseCase = publicarArquivoUseCase;
    }

    public Mono<ServerResponse> upload(ServerRequest request) {
        return request.multipartData().flatMap(multipartData -> {
            Part filePartRaw = multipartData.getFirst("file");
            if (!(filePartRaw instanceof FilePart filepart)) {
                return ServerResponse.badRequest()
                        .bodyValue(Map.of("error", "O campo 'file' é obrigatório e deve ser um arquivo."));
            }

            Part sourcePart = multipartData.getFirst("source");
            SourceContext sourceContext = SourceContext.fromCodigo(
                    sourcePart instanceof FormFieldPart field ? field.value() : "origem-desconhecida");

            return DataBufferUtils.join(filepart.content())
                    .flatMap(dataBuffer -> {
                        byte[] bytes = new byte[dataBuffer.readableByteCount()];
                        dataBuffer.read(bytes);
                        DataBufferUtils.release(dataBuffer);
                        var command = new PublicarArquivoCommand(filepart.filename(), bytes, sourceContext);
                        return publicarArquivoUseCase.executar(command);
                    }).flatMap(caminhoDataLake -> ServerResponse.created(URI.create("/" + caminhoDataLake))
                            .bodyValue(Map.of(
                                    "status", "Arquivo enviado para o Datalake",
                                    "caminho", caminhoDataLake)))
                    .onErrorResume(e -> ServerResponse.status(HttpStatus.INTERNAL_SERVER_ERROR)
                            .bodyValue(Map.of("erro", "Falha ao processar arquivo: " + e.getMessage())));
        });
    }

}
