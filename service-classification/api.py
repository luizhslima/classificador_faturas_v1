from fastapi import FastAPI
from contextlib import asynccontextmanager
from transformers import pipeline
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer, util
import torch
import numpy as np

models = {}

@asynccontextmanager
async def lifespan(app:FastAPI):
    models['encoder'] = SentenceTransformer('intfloat/multilingual-e5-large')
    print('Modelo')
    yield
    models.clear()

app = FastAPI(lifespan=lifespan)

class ClassifyRequest(BaseModel):
    text: str
    labels: list[str]

class ClassifyResponse(BaseModel):
    top_label: str
    confidence: float
    all: dict[str, float]

class BatchRequest(BaseModel):
    texts: list[str]
    labels: list[str]

def classify_texts(texts: list[str], labels: list[str]) -> list[dict]:
    model = models["encoder"]

    sentences = texts + labels
    embeddings = model.encode(sentences, normalize_embeddings=True)

    text_embs  = embeddings[:len(texts)]
    label_embs = embeddings[len(texts):]

    results = []
    for text, text_emb in zip(texts, text_embs):
        scores = np.dot(label_embs, text_emb).tolist()
        ranked = sorted(zip(labels, scores), key=lambda x: x[1], reverse=True)
        top_label, top_score = ranked[0]
        results.append({
            "text": text,
            "top_label": top_label,
            "confidence": round(top_score, 4),
            "all": {label: round(score, 4) for label, score in ranked}
        })

    return results

@app.post('/classify')
def classify(req: ClassifyRequest):
    result = classify_texts([req.text], req.labels)[0]
    return ClassifyResponse(
        top_label=result["top_label"],
        confidence=result["confidence"],
        all=result["all"]
    )


@app.post("/classify/batch")
def classify_batch(req: BatchRequest):
    return classify_texts(req.texts, req.labels)