package com.api.service.ingestao.domain.model.types;

public enum TipoArquivo {
    CSV("text/csv", "csv"),
    PDF("application/pdf", "pdf");

    private final String contentType;
    private final String extensao;

    TipoArquivo(String contentType, String extensao) {
        this.contentType = contentType;
        this.extensao = extensao;
    }

    public String getContentType() { return contentType; }
    public String getExtensao()    { return extensao; }

    public static TipoArquivo detectar(byte[] bytes, String caminho) {
        if (bytes[0] == '%' && bytes[1] == 'P' && bytes[2] == 'D' && bytes[3] == 'F') {
            return PDF;
        }
        if (caminho.toLowerCase().endsWith(".csv")) {
            return CSV;
        }
        throw new IllegalArgumentException("Formato não suportado: " + caminho);
    }
}
