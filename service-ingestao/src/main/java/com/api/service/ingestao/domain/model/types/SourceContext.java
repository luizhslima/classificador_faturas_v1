package com.api.service.ingestao.domain.model.types;

import java.util.Locale;

public enum SourceContext {
    WEB("web"),
    API("api"),
    WORKER("worker"),
    ORIGEM_DESCONHECIDA("origem-desconhecida"),
    NUBANK("nubank"),
    C6BANK("c6");

    private final String codigo;

    SourceContext(String codigo) {
        this.codigo = codigo;
    }

    public String getCodigo() {
        return codigo;
    }

    public static SourceContext fromCodigo(String valor) {
        if (valor == null || valor.isBlank()) {
            return ORIGEM_DESCONHECIDA;
        }

        String normalizado = valor.trim().toLowerCase(Locale.ROOT);
        for (SourceContext contexto : values()) {
            if (contexto.codigo.equals(normalizado)) {
                return contexto;
            }
        }

        return ORIGEM_DESCONHECIDA;
    }

    @Override
    public String toString() {
        return codigo;
    }
}
