"""Inferencia por lotes: aplica el modelo de sentimiento a las reseñas de gold.fct_reviews.

Guarda el resultado en la tabla ml.review_sentiment del mismo DuckDB, para que dbt la cruce
con fct_reviews. Es incremental: solo puntúa las reseñas que aún no tienen predicción.

Uso:
  uv run --extra gold --extra ml python -m gamepulse.ml.predict_sentiment              # todas las pendientes
  uv run --extra gold --extra ml python -m gamepulse.ml.predict_sentiment --limit 500  # prueba rápida
"""

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "warehouse" / "gamepulse.duckdb"
MODEL_DIR = ROOT / "models" / "sentiment"


def connect(read_only: bool) -> duckdb.DuckDBPyConnection:
    # dbt escribe en el mismo fichero cada hora durante unos segundos: reintentar si está bloqueado
    for attempt in range(20):
        try:
            return duckdb.connect(str(DB_PATH), read_only=read_only)
        except duckdb.IOException:
            if attempt == 19:
                raise
            time.sleep(5)
    raise RuntimeError("unreachable")


def load_pending(limit: int | None) -> pd.DataFrame:
    con = connect(read_only=True)
    try:
        exists = con.execute(
            "select count(*) from information_schema.tables "
            "where table_schema = 'ml' and table_name = 'review_sentiment'"
        ).fetchone()[0]
        done_filter = (
            "and recommendationid not in (select recommendationid from ml.review_sentiment)" if exists else ""
        )
        sql = f"""
            select recommendationid, review
            from gold.fct_reviews
            where review is not null and length(trim(review)) > 0 {done_filter}
            {f'limit {limit}' if limit else ''}
        """
        return con.execute(sql).df()
    finally:
        con.close()  # no mantener el fichero abierto durante la inferencia: bloquearía a dbt


def predict(texts: list[str], batch_size: int) -> tuple[np.ndarray, np.ndarray]:
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(device).eval()

    # ordenar por longitud: lotes con textos parecidos = menos relleno = más rápido
    order = np.argsort([len(t) for t in texts])
    probs = np.empty(len(texts), dtype=np.float32)
    t0 = time.time()
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            idx = order[i : i + batch_size]
            enc = tokenizer([texts[j] for j in idx], truncation=True, max_length=128, padding=True, return_tensors="pt")
            logits = model(**{k: v.to(device) for k, v in enc.items()}).logits
            probs[idx] = torch.softmax(logits, dim=-1)[:, 1].float().cpu().numpy()  # prob. de "positiva"
            done = min(i + batch_size, len(texts))
            if (i // batch_size) % 50 == 0 or done == len(texts):
                rate = done / max(time.time() - t0, 1e-6)
                print(f"  {done}/{len(texts)} reseñas · {rate:.0f}/s · faltan ~{(len(texts) - done) / rate / 60:.0f} min")
    return (probs >= 0.5).astype(int), probs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="máximo de reseñas (prueba)")
    parser.add_argument("--batch", type=int, default=64)
    args = parser.parse_args()

    df = load_pending(args.limit)
    print(f"Reseñas pendientes de puntuar: {len(df)}")
    if df.empty:
        return

    labels, probs = predict(df["review"].tolist(), args.batch)
    out = pd.DataFrame(
        {
            "recommendationid": df["recommendationid"],
            "sentiment_pred": labels,          # 1 = positiva, 0 = negativa
            "sentiment_score": probs,          # probabilidad de positiva (0–1)
            "model_version": MODEL_DIR.name,
            "scored_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }
    )

    con = connect(read_only=False)
    try:
        con.execute("create schema if not exists ml")
        con.register("out_df", out)
        con.execute("create table if not exists ml.review_sentiment as select * from out_df limit 0")
        con.execute("insert into ml.review_sentiment select * from out_df")
        total, pos = con.execute(
            "select count(*), round(avg(sentiment_pred) * 100, 1) from ml.review_sentiment"
        ).fetchone()
    finally:
        con.close()
    print(f"Guardadas {len(out)} predicciones · total en ml.review_sentiment: {total} ({pos}% positivas)")


if __name__ == "__main__":
    main()
