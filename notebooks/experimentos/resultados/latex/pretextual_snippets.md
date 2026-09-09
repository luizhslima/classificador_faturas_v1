# Trechos p/ pré-textuais e Cap5 (números reais)

- CER Docling: 5,72% (de 52,8% do Tesseract); casamento exato 86,2%.
- Base rotulada: 1660 transações reais (C6+Nubank), 11 categorias, 74% via dicionário léxico.
- Splits: 1150 treino / 176 validação / 334 teste-cego (por estabelecimento).
- TF-IDF+RF: F1-Macro 69.3% / acurácia 84.7% (CV 92.7%).
- TF-IDF+NB: F1-Macro 63.6% / acurácia 88.3%.
- RAG PGVector: F1-Macro 56.2% / latência 1.4 ms.
- ByT5-small: F1-Macro 48.3%.
- Agente híbrido: acurácia 61.4% / F1-Macro 60.0% / HITL 4.5% / latência 6.5~s.
- Nenhum modelo atinge 85% de F1-Macro no teste-cego por estabelecimento.
