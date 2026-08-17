package com.api.service.ingestao.domain.model;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDate;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;

import com.api.service.ingestao.application.utils.EncondingUtils;
import com.api.service.ingestao.domain.model.types.TipoArquivo;
import com.api.service.ingestao.infrastructure.exception.BusinessRuleException;

public class ArquivoIngestao {
    private final String id;
    private final String nomeOriginal;
    private final byte[] conteudo;
    private final String sourceContext;

    public ArquivoIngestao(String nomeOriginal, byte[] conteudo, String sourceContext) {
        if (conteudo == null || conteudo.length == 0) throw new BusinessRuleException("Arquivo vazio.");
        
        this.id = UUID.randomUUID().toString();
        this.nomeOriginal = nomeOriginal;
        this.conteudo = conteudo;
        this.sourceContext = sourceContext;
    }

    // O domínio desta aplicação só gera caminhos para a camada Bronze
    public String gerarCaminhoBronze() {
        LocalDate hoje = LocalDate.now();
        String extensao = nomeOriginal.substring(nomeOriginal.lastIndexOf(".") + 1).toLowerCase();
        
        return String.format("bronze/source=%s/year=%d/month=%02d/day=%02d/%s/original.%s",
                this.sourceContext, hoje.getYear(), hoje.getMonthValue(), hoje.getDayOfMonth(), this.id, extensao);
    }

    public byte[] getConteudo() {
        return conteudo;
    }

    public String getId() {
        return id;
    }

    public String getContext(){
        return sourceContext;
    }

    public String getExtensao() {
        return TipoArquivo.detectar(this.conteudo, this.nomeOriginal).getExtensao();
    }

    public String getContentType() {
        return TipoArquivo.detectar(this.conteudo, this.nomeOriginal).getContentType();
    }

    public Map<String, String> getMetadados() {
        return Map.of(
                "id-arquivo", this.id,
                "nomeOriginal", this.nomeOriginal,
                "source-context", this.sourceContext,
                "formato-detectado", this.getExtensao(),
                "hash-sha256", calcularHash(this.conteudo),
                "versao-pipeline", "1.0",
                "timestamp-ingestao", String.valueOf(System.currentTimeMillis()),
                "tamanho-bytes", String.valueOf(this.conteudo.length),
                "requer-ocr", String.valueOf(this.getContentType().equals(TipoArquivo.PDF.getContentType())),
                "enconding", detectarEncoding(this.conteudo)
            );
    }

    private static String calcularHash(byte[] bytes) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(bytes));
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }

    private static String detectarEncoding(byte[] bytes) {
        // use ICU4J ou UniversalDetector para detectar UTF-8, ISO-8859-1 etc
        return EncondingUtils.identificarEncoding(bytes);
    }
}
