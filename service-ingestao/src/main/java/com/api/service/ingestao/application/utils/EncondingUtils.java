package com.api.service.ingestao.application.utils;

import java.nio.charset.StandardCharsets;

import com.ibm.icu.text.CharsetDetector;
import com.ibm.icu.text.CharsetMatch;

public final class EncondingUtils {

    private EncondingUtils() {
        // Construtor privado para evitar instanciação
    }

    /**
     * Detecta o encoding e aplica o fallback para UTF-8 se a confiança for baixa.
     */
    public static String identificarEncoding(byte[] dados) {
        CharsetDetector detector = new CharsetDetector();
        detector.setText(dados);
        
        CharsetMatch match = detector.detect();

        // Limiar de confiança definido para 50%
        if (match != null && match.getConfidence() >= 50) {
            System.out.println("[Log] Encoding detectado: " + match.getName() + " (Confiança: " + match.getConfidence() + "%)");
            return match.getName();
        }

        System.out.println("[Log] Confiança baixa ou nula. Aplicando fallback para UTF-8.");
        return "UTF-8";
    }

    /**
     * Transforma os bytes brutos em uma String legível usando o encoding seguro.
     */
    public static String decodificarComSeguranca(byte[] dados) {
        String encodingSeguro = identificarEncoding(dados);
        
        try {
            // Tenta criar a String com o encoding encontrado (ou o fallback)
            return new String(dados, encodingSeguro);
        } catch (Exception e) {
            // Em caso de erro bizarro (ex: nome do encoding não suportado pela JVM), 
            // força a barra com o UTF-8 nativo do Java para não quebrar a execução
            return new String(dados, StandardCharsets.UTF_8);
        }
    }

}
