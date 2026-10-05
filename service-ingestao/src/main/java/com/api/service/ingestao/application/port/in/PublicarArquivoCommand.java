package com.api.service.ingestao.application.port.in;

import com.api.service.ingestao.domain.model.types.SourceContext;

public record PublicarArquivoCommand(
    String nomeArquivo,
    byte[] conteudo,
    SourceContext sourceContext
) {
    
}
