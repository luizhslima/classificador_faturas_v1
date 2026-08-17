package com.api.service.ingestao.application.port.in;

public record PublicarArquivoCommand(
    String nomeArquivo,
    byte[] conteudo,
    String sourceContext
) {
    
}
