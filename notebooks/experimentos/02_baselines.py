"""
Etapa 2 — Baselines clássicos (representação esparsa TF-IDF).

  Baseline 1: TF-IDF (char + word n-grams) + Multinomial Naive Bayes
  Baseline 2: TF-IDF (char + word n-grams) + Random Forest

Protocolo: validação cruzada 5-fold sobre treino+validação (F1-macro) e avaliação
final no conjunto de teste-cego congelado. Latência medida como tempo médio de
inferência por transação no teste.
"""
from __future__ import annotations

import time

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline

import common as C


def _features():
    return ColumnTransformer(
        [
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1,
                                     sublinear_tf=True), "descricao"),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1),
             "descricao"),
        ]
    )


def roda(nome, clf, params):
    tr, val, test = C.carregar_splits()
    dev = C.pd.concat([tr, val], ignore_index=True)
    pipe = Pipeline([("feat", _features()), ("clf", clf)])

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=C.RANDOM_STATE)
    cv = cross_val_score(pipe, dev[["descricao"]], dev["categoria"], cv=skf,
                         scoring="f1_macro")
    cv_scores = {"f1_macro_mean": float(cv.mean()), "f1_macro_std": float(cv.std())}

    pipe.fit(dev[["descricao"]], dev["categoria"])
    t0 = time.perf_counter()
    y_pred = pipe.predict(test[["descricao"]])
    lat = (time.perf_counter() - t0) / len(test) * 1000.0

    C.registrar_resultado(nome, params, test["categoria"].tolist(), list(y_pred), lat,
                          cv_scores=cv_scores, tags={"familia": "baseline_esparso"})


if __name__ == "__main__":
    roda("tfidf_naive_bayes", MultinomialNB(),
         {"vectorizer": "tfidf word(1,2)+char_wb(2,4)", "classificador": "MultinomialNB",
          "cv": "5-fold"})
    roda("tfidf_random_forest",
         RandomForestClassifier(n_estimators=400, random_state=C.RANDOM_STATE, n_jobs=-1,
                                class_weight="balanced_subsample"),
         {"vectorizer": "tfidf word(1,2)+char_wb(2,4)", "classificador": "RandomForest(400)",
          "cv": "5-fold"})
