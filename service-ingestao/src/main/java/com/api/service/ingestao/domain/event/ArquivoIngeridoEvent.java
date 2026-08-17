package com.api.service.ingestao.domain.event;


public record ArquivoIngeridoEvent(
    String idArquivo,
    String sourceContext,
    String caminhoMinio, // O worker usará isso para dar o GET no bucket
    long timestampCriacao
) {}
