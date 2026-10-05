package com.api.service.ingestao.domain.event;

import com.api.service.ingestao.domain.model.types.SourceContext;

public record ArquivoIngeridoEvent(
    String idArquivo,
    SourceContext sourceContext,
    String caminhoMinio, // O worker usará isso para dar o GET no bucket
    long timestampCriacao
) {}
