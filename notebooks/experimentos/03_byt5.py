"""
Etapa 3 — SOTA neural: fine-tuning do ByT5 (tokenização a nível de byte).

Formulação text-to-text: entrada = descrição ruidosa da transação,
alvo = nome da categoria canônica. Na inferência, a saída gerada é ancorada
à categoria canônica mais próxima (distância de Levenshtein normalizada).

Tenta google/byt5-base; cai para google/byt5-small se a VRAM (8 GB) estourar.
"""
from __future__ import annotations

import os
import time

import numpy as np
import torch
from datasets import Dataset
from rapidfuzz import process, fuzz
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)

import common as C

MAX_IN, MAX_OUT = 64, 16
PROMPT = "classificar categoria da transacao: "


def ancorar(texto: str) -> str:
    m = process.extractOne(texto.strip(), C.CATEGORIAS, scorer=fuzz.WRatio)
    return m[0] if m else C.CATEGORIAS[-1]


def preparar(ds: "C.pd.DataFrame", tok):
    def _fn(batch):
        x = tok([PROMPT + d for d in batch["descricao"]], max_length=MAX_IN,
                truncation=True)
        y = tok(text_target=list(batch["categoria"]), max_length=MAX_OUT, truncation=True)
        x["labels"] = y["input_ids"]
        return x

    return Dataset.from_pandas(ds[["descricao", "categoria"]]).map(
        _fn, batched=True, remove_columns=["descricao", "categoria"]
    )


def treinar(model_name: str, bs: int, accum: int):
    tr, val, test = C.carregar_splits()
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    args = Seq2SeqTrainingArguments(
        output_dir=str(C.RESULTS / "byt5_ckpt"),
        per_device_train_batch_size=bs,
        per_device_eval_batch_size=bs,
        gradient_accumulation_steps=accum,
        learning_rate=5e-4,
        num_train_epochs=12,
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_steps=20,
        save_strategy="no",
        report_to=[],
        predict_with_generate=True,
        generation_max_length=MAX_OUT,
        bf16=bf16,
        fp16=torch.cuda.is_available() and not bf16,
        dataloader_num_workers=0,
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=preparar(C.pd.concat([tr, val]), tok),
        data_collator=DataCollatorForSeq2Seq(tok, model=model),
        processing_class=tok,
    )
    trainer.train()

    t0 = time.perf_counter()
    enc = tok([PROMPT + d for d in test["descricao"]], return_tensors="pt",
              padding=True, truncation=True, max_length=MAX_IN).to(model.device)
    with torch.no_grad():
        out = model.generate(**enc, max_length=MAX_OUT, num_beams=1)
    lat = (time.perf_counter() - t0) / len(test) * 1000.0
    raw = tok.batch_decode(out, skip_special_tokens=True)
    y_pred = [ancorar(r) for r in raw]
    return test["categoria"].tolist(), y_pred, lat, model_name


def main():
    tentativas = [("google/byt5-small", 16, 1)]
    if os.getenv("BYT5_BASE"):
        tentativas.insert(0, ("google/byt5-base", 4, 4))
    for model_name, bs, accum in tentativas:
        try:
            print(f"\n=== treinando {model_name} ===")
            y_true, y_pred, lat, used = treinar(model_name, bs, accum)
            C.registrar_resultado(
                "byt5_finetuning",
                {"modelo_base": used, "epochs": 18, "lr": 3e-4, "max_in": MAX_IN,
                 "ancoragem": "levenshtein->categoria_canonica"},
                y_true, y_pred, lat, tags={"familia": "sota_neural"},
            )
            break
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            print(f"[OOM] {model_name} não coube na VRAM, tentando menor...")
        except Exception as e:  # noqa
            print(f"[erro] {model_name}: {e}")
            if "small" in model_name:
                raise


if __name__ == "__main__":
    main()
