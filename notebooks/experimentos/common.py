"""
Utilidades compartilhadas para os experimentos de classificação do Capítulo 4.

- Taxonomia canônica de 14 categorias (idêntica à tabela `categorias` do Postgres).
- Construção da base rotulada de referência a partir das faturas reais do C6 Bank
  (categoria nativa do emissor + refino por dicionário léxico de alta precisão).
- Split estratificado 70/15/15 reprodutível.
- Métricas multiclasse e helper de logging no MLflow.
"""
from __future__ import annotations

import glob
import hashlib
import os
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

try:  # evita UnicodeEncodeError (emojis do MLflow) em stdout cp1252 no Windows
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
PROCESSED = DATA / "processed"
RESULTS = Path(__file__).resolve().parent / "resultados"
PROCESSED.mkdir(parents=True, exist_ok=True)
RESULTS.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO / "notebooks" / "modules"))

RANDOM_STATE = 42

# ---------------------------------------------------------------------------
# Taxonomia canônica (14 categorias) — espelha a tabela `categorias` (id 1..14)
# ---------------------------------------------------------------------------
CATEGORIAS = [
    "Alimentação",
    "Transporte",
    "Saúde",
    "Moradia",
    "Lazer e Entretenimento",
    "Tecnologia",
    "Marketplace / E-commerce",
    "Vestuário",
    "Beleza e Cuidados Pessoais",
    "Educação",
    "Pets",
    "Serviços Financeiros",
    "Doações e Presentes",
    "Despesas Diversas / Outros",
]
CAT_TO_ID = {c: i + 1 for i, c in enumerate(CATEGORIAS)}
ID_TO_CAT = {i + 1: c for i, c in enumerate(CATEGORIAS)}

# ---------------------------------------------------------------------------
# 1) Mapa da categoria NATIVA do emissor (C6) -> taxonomia canônica
# ---------------------------------------------------------------------------
C6_NATIVO_PARA_CANONICO = {
    "Transporte": "Transporte",
    "T&E": "Transporte",
    "T&E Companhia aérea": "Transporte",
    "T&E Hotel": "Transporte",
    "Automotivo": "Transporte",
    "Relacionados a Automotivo": "Transporte",
    "Restaurante / Lanchonete / Bar": "Alimentação",
    "Supermercados / Mercearia / Padarias / Lojas de Conveniência": "Alimentação",
    "Entretenimento": "Lazer e Entretenimento",
    "Recreativo": "Lazer e Entretenimento",
    "TV por assinatura / Serviços de rádio": "Lazer e Entretenimento",
    "Assistência médica e odontológica": "Saúde",
    "Aparelhos auditivos": "Saúde",
    "Serviços pessoais": "Beleza e Cuidados Pessoais",
    "Vestuário / Roupas": "Vestuário",
    "Departamento / Desconto": "Marketplace / E-commerce",
    "Especialidade varejo": "Marketplace / E-commerce",
    "Marketing Direto": "Marketplace / E-commerce",
    "Representantes e Galerias de Arte": "Marketplace / E-commerce",
    "Serviços de telecomunicações": "Moradia",
    "Casa / Escritório Mobiliário": "Moradia",
    "Materiais de construção para casa": "Moradia",
    "Elétrico": "Tecnologia",
    "Educacional": "Educação",
    "Serviços financeiros": "Serviços Financeiros",
    "Serviços Profissionais": "Despesas Diversas / Outros",
    "Empresa para empresa": "Despesas Diversas / Outros",
    "Empresa serviços": "Despesas Diversas / Outros",
    "Associação": "Despesas Diversas / Outros",
    "Consertos em Geral": "Despesas Diversas / Outros",
}

# Categorias nativas descartadas (pagamentos, estornos, tarifas de fatura, etc.)
C6_NATIVO_DESCARTADO = {"-", "", "nan"}
_LIXO_DESC = re.compile(
    r"inclusao de pagamento|estorno|anuidade|pagamento recebido|"
    r"credito rotativo|iof |encargos|multa|juros de|saldo em atraso",
    re.I,
)

# ---------------------------------------------------------------------------
# 2) Dicionário léxico de ALTA PRECISÃO (vence a categoria nativa)
#    Ordem importa: regras específicas antes de genéricas (marketplace por último).
# ---------------------------------------------------------------------------
_REGRAS_LEXICAIS: list[tuple[str, str]] = [
    # -- Transporte
    (r"\buber\b|\b99app\b|\b99 ?pop\b|\bcabify\b|\bindriver\b|\bblablacar\b", "Transporte"),
    (r"posto |ipiranga|\bshell\b|petrobras|br distribuidora|ale combust|gasolina|\bcombust", "Transporte"),
    (r"estacionament|\bzul\b|zona azul|\bsem parar\b|conectcar|veloe|\bpedagio\b", "Transporte"),
    (r"latam|\bgol \b|gol transp|azul linhas|azul via|passagem aere|companhia aerea|emirates air|\btam \b", "Transporte"),
    (r"\bcptm\b|\bmetro \b|bilhete unico|\briocard\b|\bbom \b", "Transporte"),
    # -- Alimentação
    (r"ifood|\bifd\b|ifd\*|\brappi\b|zé delivery|ze delivery|\baiqfome\b", "Alimentação"),
    (r"mc ?donald|arcos dourados|burger king|\bbk \b|habibs|subway|giraffas|bobs |spoleto|outback", "Alimentação"),
    (r"pizzaria|pizza|restaurante|lanchonete|churrascar|hamburgu|\bbar \b|\bboteco\b|cafeteria|\bcafe\b|padaria|confeitaria|doceria|sorvete|\bacai\b|gelateria", "Alimentação"),
    (r"supermerc|atacadist|\bassai\b|\bassaí\b|carrefour|pao de acucar|pão de açúcar|extra |big bompreco|\bnagumo\b|\bdia \b|hortifruti|hortigranj|quitanda|mercearia|\bsacolao\b|takahashi|comercial piracicaba|cacau show|kopenhagen|casa pao|casa de carnes|acougue|açougue|avicola|frango", "Alimentação"),
    # -- Saúde
    (r"drogari|\bdroga \b|drogal|farmacia|farmácia|drogasil|pacheco|pague menos|panvel|raia |ultrafarma|nissei|\bsp drogar", "Saúde"),
    (r"\botica\b|\bótica\b|oculos|hospital|clinica|clínica|laborator|\blab \b|odonto|dentist|\bmedic|fisioterap|psicolog|\bexame|\bvacina|orthofen|unimed|hapvida|amil |porto seg saude", "Saúde"),
    # -- Pets  (antes de Saúde/Alimentação genéricos já cobertos acima)
    (r"\bpetz\b|\bcobasi\b|petlove|pet ?shop|\bpetshop\b|veterinar|\bvet \b|agropet|\bracao\b|\bração\b|petcenter|petland", "Pets"),
    # -- Beleza e Cuidados Pessoais
    (r"o ?boticario|o ?boticário|\bnatura\b|\bavon\b|\beudora\b|\bsephora\b|\bquem disse berenice\b|\bqdb\b|barbear|\bsalao\b|\bsalão\b|cabelele|manicure|\besmalteria\b|\bperfum|the beauty box|\bmac \b", "Beleza e Cuidados Pessoais"),
    # -- Educação
    (r"\balura\b|\budemy\b|coursera|\bebac\b|\bfiap\b|\bdio\b|origamid|rocketseat|\bkulti|duolingo|\bbabbel\b|open english|\bcultura ing|escola |colegio|colégio|faculdade|universidad|\buniv \b|\bpos \b|\bmba\b|\bcurso\b|\bkindle\b|amazon kindle|livraria|\blivro|\bsebo\b", "Educação"),
    # -- Lazer e Entretenimento
    (r"netflix|spotify|disney|\bhbo\b|\bmax\b|help ?hbo|help ?max|prime video|globoplay|\bdeezer\b|paramount|\bstar\+|\bmubi\b|crunchyroll|youtube ?premium|apple\.com/bill|apple tv|\bappletv\b", "Lazer e Entretenimento"),
    (r"\bsteam\b|playstat|\bxbox\b|nintendo|\bxsolla\b|\bnuuvem\b|epicgames|epic games|\briot\b|\bblizzard\b|garena|\bgog\b|\btwitch\b|\bkick\b|\bdiscord\b|\bpsn\b|game ?pass|\bmojang\b", "Lazer e Entretenimento"),
    (r"cinema|cinemark|cinepolis|\buci \b|\bkinoplex\b|ingresse|ingresso|\bsympla\b|eventim|\bticketm|tomorrowland|\bshow\b|teatro|\bparque\b|hopi hari|beto carrero|\bzoo\b|aquario|\bmuseu\b|\bbaladas?\b|boliche|bowling|\bpaintball\b|\bkart\b|mergulho|\bcanoa\b", "Lazer e Entretenimento"),
    # -- Tecnologia / Serviços digitais
    (r"abacus\.ai|openrouter|openai|anthropic|\bclaude\b|\bcursor\b|\bgithub\b|\brailway\b|digitalocea|\bvercel\b|\bnetlify\b|\bheroku\b|\baws\b|amazon web|google cloud|\bgcp\b|\bazure\b|cloudflare|\bumbler\b|hostgator|hostinger|\bkinghost\b|\bfl cloud\b|\bvps\b|\bhosting\b", "Tecnologia"),
    (r"\bcanva\b|adobe|\bfigma\b|\bnotion\b|\bslack\b|\bzoom\b|jetbrains|microsoft|\boffice 365\b|\bmicrosoft 365\b|google one|\bicloud\b|\bdropbox\b|\bmega\b|\bevernote\b|\b1password\b|\bnordvpn\b|\bexpressvpn\b|grammarly|\bmidjourney\b|\breplit\b|\bwix\b|\bgodaddy\b|\bnamecheap\b|\bmercado livre.*produto.*eletr", "Tecnologia"),
    (r"\bkabum\b|\bpichau\b|\bterabyte\b|\bgigantec\b|casas bahia.*(celular|notebook)|magazine.*(celular|notebook)|\bapple store\b|\biplace\b|\bsamsung\b", "Tecnologia"),
    # -- Vestuário
    (r"lojas renner|\brenner\b|riachuelo|\bc&a\b|\bcea \b|\bhering\b|\blacoste\b|\bzara\b|\bnike\b|\badidas\b|\bpuma\b|centauro|\bnetshoes\b|decathlon|pernambucana|\bmarisa\b|\bmartan\b|\bmalwee\b|calvin klein|\bcolcci\b|\bosklen\b|\breserva\b|\banimale\b|calcados|calçados|\bsapataria\b|\bpompeia\b|\bhavaianas\b|\bmizuno\b|\bfila \b|\bkeds\b|\btrack.?field\b|\bfutfanat|\bcamisa", "Vestuário"),
    # -- Moradia / Contas / Serviços residenciais
    (r"\benel\b|\bcpfl\b|\belektro\b|\blight \b|\bcemig\b|\bcopel\b|\bcelesc\b|energia elet|\bsabesp\b|\bcedae\b|\bcopasa\b|\bsanepar\b|\bcomgas\b|\bcomgás\b|ultragaz|\bnaturgy\b|liquigas|\bgas \b|\bgás\b|\bcondominio\b|\bcondomínio\b|\baluguel\b|\biptu\b|imobiliaria|imobiliária", "Moradia"),
    (r"\bclaro\b|\bvivo\b|\btim \b|\boi \b|\bnet \b|\bsky\b|america net|americanet|\bnextel\b|\bgvt\b|telecom|internet |banda larga|\bfibra\b", "Moradia"),
    (r"leroy merlin|\bc&c\b|telhanorte|\bdicico\b|\bobramax\b|casa tokio|tok ?stok|\bmadeira madeira\b|\bmobly\b|\betna\b|materiais de constru|\bferragens?\b|\bmarcenaria\b|\bvidracaria\b", "Moradia"),
    # -- Doações e Presentes
    (r"\bdoacao\b|\bdoação\b|\bvakinha\b|\bapae\b|\bgofundme\b|catarse|benfeitoria|cruz vermelha|\bunicef\b|\bteleton\b|\bdizimo\b|\bdízimo\b|\boferta igreja\b|\bigreja\b|\bpastoral\b|\bcaritas\b|\bcáritas\b", "Doações e Presentes"),
    # -- Serviços Financeiros
    (r"\btarifa\b|\banuidade\b|\biof\b|juros |\bsaque\b|\bcambio\b|\bcâmbio\b|corretora|\bxp inv|\brico \b|\bclear\b|\bnuinvest\b|\bbinance\b|\bmercado bitcoin\b|\bfoxbit\b|seguro |\bprevidencia\b|consorcio|consórcio|emprestimo|empréstimo|\bfatura\b|\bboleto\b", "Serviços Financeiros"),
    # -- Marketplace / E-commerce  (genérico, por último)
    (r"mercadolivre|mercado livre|mercadopago|mercado pago|\bmercpag\b|\bmeli\b|\bmelimais\b|\bml\*|\bmlp\*", "Marketplace / E-commerce"),
    (r"\bamazon\b|\bamzn\b|amazonmktplc|amazon mktp|amazon marketplace|amazon br", "Marketplace / E-commerce"),
    (r"\bshopee\b|\bshein\b|aliexpress|\bali\*|alibaba|\bwish\b|\btemu\b", "Marketplace / E-commerce"),
    (r"magazine ?luiza|\bmagalu\b|americanas|\bsubmarino\b|casas ?bahia|\bponto frio\b|\bextra\.com|\bshoptime\b|\bdafiti\b|\benjoei\b|\bolx\b|\belo7\b|mercado ?shops", "Marketplace / E-commerce"),
]
_REGRAS_LEXICAIS_COMPILADAS = [(re.compile(p, re.I), c) for p, c in _REGRAS_LEXICAIS]


def _strip_accents_lower(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()


def rotular_por_regra(descricao: str) -> str | None:
    """Aplica o dicionário léxico de alta precisão. Retorna categoria canônica ou None."""
    if not descricao:
        return None
    alvo = _strip_accents_lower(descricao)
    for rx, cat in _REGRAS_LEXICAIS_COMPILADAS:
        if rx.search(alvo):
            return cat
    return None


def rotular_transacao(descricao: str, categoria_nativa: str) -> str | None:
    """Regra léxica (precedência) -> categoria nativa mapeada -> None (descartar)."""
    cat = categoria_nativa.strip() if isinstance(categoria_nativa, str) else ""
    if cat in C6_NATIVO_DESCARTADO or _LIXO_DESC.search(str(descricao) or ""):
        return None
    por_regra = rotular_por_regra(descricao)
    if por_regra:
        return por_regra
    return C6_NATIVO_PARA_CANONICO.get(cat)  # None se categoria nativa desconhecida


# ---------------------------------------------------------------------------
# Construção da base rotulada
# ---------------------------------------------------------------------------
def _parse_valor(x) -> float:
    try:
        return float(str(x).replace(".", "").replace(",", ".")) if "," in str(x) else float(x)
    except Exception:
        return np.nan


def carregar_c6_rotulado() -> pd.DataFrame:
    """Consolida todas as faturas CSV do C6, deduplica e aplica a rotulagem de referência."""
    files = glob.glob(str(DATA / "datasets" / "C6" / "**" / "Fatura_*.csv"), recursive=True)
    frames = []
    for f in files:
        try:
            d = pd.read_csv(f, sep=";", dtype=str)
            frames.append(d)
        except Exception:
            pass
    raw = pd.concat(frames, ignore_index=True)
    raw = raw.rename(
        columns={
            "Data de Compra": "data",
            "Categoria": "categoria_nativa",
            "Descrição": "descricao",
            "Parcela": "parcela",
            "Valor (em R$)": "valor",
            "Final do Cartão": "final_cartao",
        }
    )
    raw["valor"] = raw["valor"].map(_parse_valor)
    raw["descricao"] = raw["descricao"].fillna("").str.strip()
    raw = raw.drop_duplicates(subset=["data", "descricao", "parcela", "valor", "final_cartao"])
    raw = raw[raw["descricao"] != ""]
    raw = raw[raw["valor"] > 0]  # remove pagamentos/estornos negativos

    raw["categoria"] = [
        rotular_transacao(desc, catn)
        for desc, catn in zip(raw["descricao"], raw["categoria_nativa"])
    ]
    df = raw[raw["categoria"].notna()].copy()
    df["fonte_dataset"] = "c6_real"
    df["categoria_id"] = df["categoria"].map(CAT_TO_ID)
    df["metodo_rotulo"] = np.where(
        df["descricao"].map(lambda d: rotular_por_regra(d) is not None),
        "regra_lexical",
        "categoria_emissor",
    )
    return df[
        ["data", "descricao", "valor", "parcela", "final_cartao",
         "categoria_nativa", "categoria", "categoria_id", "metodo_rotulo", "fonte_dataset"]
    ].reset_index(drop=True)


def carregar_nubank_bruto() -> pd.DataFrame:
    """Faturas Nubank (sem rótulo do emissor) — usadas para gravação no BD e HITL."""
    files = glob.glob(str(DATA / "datasets" / "nubank" / "*.csv"))
    frames = []
    for f in files:
        try:
            d = pd.read_csv(f, dtype=str)
            frames.append(d)
        except Exception:
            pass
    raw = pd.concat(frames, ignore_index=True).rename(
        columns={"date": "data", "title": "descricao", "amount": "valor"}
    )
    raw["valor"] = raw["valor"].map(_parse_valor)
    raw["descricao"] = raw["descricao"].fillna("").str.strip()
    raw = raw.drop_duplicates(subset=["data", "descricao", "valor"])
    raw = raw[(raw["descricao"] != "") & (raw["valor"] > 0)]
    raw = raw[~raw["descricao"].str.contains(_LIXO_DESC, na=False)]
    raw["categoria_regra"] = raw["descricao"].map(rotular_por_regra)
    raw["fonte_dataset"] = "nubank_real"
    return raw.reset_index(drop=True)


def chave_estabelecimento(descricao: str) -> str:
    return re.sub(r"\s+", " ", _strip_accents_lower(descricao)).strip()


def split_estratificado(df: pd.DataFrame, seed: int = RANDOM_STATE):
    """70/15/15 treino/validação/teste-cego.

    O split é feito por *estabelecimento* (string de descrição normalizada): todas as
    ocorrências de um mesmo estabelecimento caem no mesmo split, impedindo vazamento
    de merchant entre treino e teste. A estratificação por categoria é feita sobre o
    rótulo majoritário de cada estabelecimento.
    """
    from sklearn.model_selection import train_test_split

    df = df.copy()
    df["_chave"] = df["descricao"].map(chave_estabelecimento)
    grp = (
        df.groupby("_chave")["categoria"]
        .agg(lambda s: s.value_counts().index[0])
        .reset_index()
        .rename(columns={"categoria": "_cat_maj"})
    )
    # categorias com <3 estabelecimentos: não dá para estratificar em 3 vias
    vc = grp["_cat_maj"].value_counts()
    grp["_estrato"] = grp["_cat_maj"].where(grp["_cat_maj"].map(vc) >= 3, "__rara__")

    g_tr, g_tmp = train_test_split(
        grp, test_size=0.30, random_state=seed, stratify=grp["_estrato"]
    )
    try:
        vc2 = g_tmp["_estrato"].value_counts()
        strat_tmp = g_tmp["_estrato"].where(g_tmp["_estrato"].map(vc2) >= 2, vc2.idxmax())
        g_val, g_test = train_test_split(
            g_tmp, test_size=0.50, random_state=seed, stratify=strat_tmp
        )
    except ValueError:
        g_val, g_test = train_test_split(g_tmp, test_size=0.50, random_state=seed)
    mapa = {}
    for name, gg in [("treino", g_tr), ("validacao", g_val), ("teste", g_test)]:
        for k in gg["_chave"]:
            mapa[k] = name
    df["split"] = df["_chave"].map(mapa)
    out = [
        df[df["split"] == s].drop(columns=["_chave"]).reset_index(drop=True)
        for s in ("treino", "validacao", "teste")
    ]
    return out[0], out[1], out[2]


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------
def metricas_multiclasse(y_true, y_pred) -> dict:
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
    )

    return {
        "acuracia": float(accuracy_score(y_true, y_pred)),
        "precisao_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }


def relatorio_por_categoria(y_true, y_pred) -> pd.DataFrame:
    from sklearn.metrics import classification_report

    rep = classification_report(
        y_true, y_pred, output_dict=True, zero_division=0, labels=CATEGORIAS
    )
    rows = []
    for cat in CATEGORIAS:
        r = rep.get(cat, {})
        rows.append(
            {
                "categoria": cat,
                "precisao": 100 * r.get("precision", 0.0),
                "recall": 100 * r.get("recall", 0.0),
                "f1": 100 * r.get("f1-score", 0.0),
                "suporte": int(r.get("support", 0)),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# MLflow
# ---------------------------------------------------------------------------
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://192.168.15.18:5000")
EXPERIMENT_NAME = "experimento_faturas"


def init_mlflow():
    import mlflow

    os.environ.setdefault("AWS_ACCESS_KEY_ID", "admin_tcc")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "senha_super_segura")
    os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", "http://192.168.15.18:9000")
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    return mlflow


DB_SYNC = os.getenv(
    "SYNC_DATABASE_URL", "postgresql+psycopg2://n8n:n8n_dev_password@192.168.15.18:5433/agent"
)
DB_ASYNC = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://n8n:n8n_dev_password@192.168.15.18:5433/agent"
)


def engine_sync():
    from sqlalchemy import create_engine

    return create_engine(DB_SYNC, connect_args={"connect_timeout": 10})


def carregar_splits():
    tr = pd.read_csv(PROCESSED / "split_treino.csv")
    val = pd.read_csv(PROCESSED / "split_validacao.csv")
    test = pd.read_csv(PROCESSED / "split_teste.csv")
    for d in (tr, val, test):
        d["descricao"] = d["descricao"].astype(str)
    return tr, val, test


def registrar_resultado(
    nome_modelo: str,
    params: dict,
    y_true,
    y_pred,
    latencia_ms: float,
    cv_scores: dict | None = None,
    tags: dict | None = None,
    extra_metrics: dict | None = None,
):
    """Loga um run no MLflow + persiste CSVs locais (métricas globais e por categoria)."""
    mlflow = init_mlflow()
    m = metricas_multiclasse(y_true, y_pred)
    m["latencia_ms"] = float(latencia_ms)
    if extra_metrics:
        m.update(extra_metrics)
    por_cat = relatorio_por_categoria(y_true, y_pred)

    with mlflow.start_run(run_name=f"cls::{nome_modelo}"):
        mlflow.set_tag("etapa", "classificacao_cap4")
        mlflow.set_tag("modelo", nome_modelo)
        for k, v in (tags or {}).items():
            mlflow.set_tag(k, v)
        for k, v in params.items():
            mlflow.log_param(k, v)
        for k, v in m.items():
            mlflow.log_metric(k, v)
        if cv_scores:
            for k, v in cv_scores.items():
                mlflow.log_metric(f"cv_{k}", v)
        cat_path = RESULTS / f"por_categoria__{nome_modelo}.csv"
        por_cat.to_csv(cat_path, index=False)
        mlflow.log_artifact(str(cat_path), "por_categoria")
        pred_path = RESULTS / f"predicoes__{nome_modelo}.csv"
        pd.DataFrame({"y_true": list(y_true), "y_pred": list(y_pred)}).to_csv(pred_path, index=False)
        mlflow.log_artifact(str(pred_path), "predicoes")

    linha = {"modelo": nome_modelo, **{k: round(v, 4) for k, v in m.items()}}
    if cv_scores:
        linha.update({f"cv_{k}": round(v, 4) for k, v in cv_scores.items()})
    consol = RESULTS / "consolidado_modelos.csv"
    df = pd.read_csv(consol) if consol.exists() else pd.DataFrame()
    df = df[df.get("modelo", pd.Series(dtype=str)) != nome_modelo] if len(df) else df
    df = pd.concat([df, pd.DataFrame([linha])], ignore_index=True)
    df.to_csv(consol, index=False)
    print(f"[{nome_modelo}] acc={m['acuracia']:.4f} f1_macro={m['f1_macro']:.4f} "
          f"lat={latencia_ms:.2f}ms")
    return m, por_cat


if __name__ == "__main__":
    df = carregar_c6_rotulado()
    print("C6 rotulado:", df.shape)
    print(df["categoria"].value_counts())
    print("\nmétodo de rótulo:")
    print(df["metodo_rotulo"].value_counts())
    nu = carregar_nubank_bruto()
    print("\nNubank bruto:", nu.shape, "| com regra:", nu["categoria_regra"].notna().sum())
