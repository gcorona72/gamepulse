"""Prepara las reseñas de Steam para entrenar el modelo de sentimiento.

Lee gold.fct_reviews (DuckDB), limpia los textos y genera tres ficheros Parquet en data/ml/:
- train y val: muestra equilibrada (misma cantidad de positivas y negativas) para que el modelo
  no aprenda a decir siempre "positiva" (en Steam ~77 % lo son).
- test: muestra con la distribución real, para medir cómo funciona en la práctica.

Uso:  uv run --extra gold --extra ml python -m gamepulse.ml.prepare_reviews
"""

import argparse
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "warehouse" / "gamepulse.duckdb"
OUT_DIR = ROOT / "data" / "ml"


def connect(path: Path) -> duckdb.DuckDBPyConnection:
    # dbt escribe en el mismo fichero cada hora durante unos segundos: reintentar si está bloqueado
    for attempt in range(10):
        try:
            return duckdb.connect(str(path), read_only=True)
        except duckdb.IOException:
            if attempt == 9:
                raise
            time.sleep(3)
    raise RuntimeError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-class", type=int, default=10_000, help="reseñas por clase (train+val)")
    parser.add_argument("--test-size", type=int, default=4_000, help="reseñas del test")
    parser.add_argument("--val-frac", type=float, default=0.1)
    parser.add_argument("--seed", type=float, default=0.42)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = connect(DB_PATH)
    con.execute(f"select setseed({args.seed})")

    # Limpieza: texto no vacío, sin duplicados de texto, longitud razonable.
    # El orden aleatorio se fija una vez para que train/val/test no se solapen.
    con.execute("""
        create temp table clean as
        select
            recommendationid,
            trim(review) as text,
            cast(voted_up as int) as label,
            language,
            random() as r
        from gold.fct_reviews
        where review is not null
          and length(trim(review)) >= 2
          and length(trim(review)) <= 2000
        qualify row_number() over (partition by lower(trim(review)) order by recommendationid) = 1
    """)

    # Test primero, con la distribución real
    con.execute(f"""
        create temp table test as
        select * from clean order by r limit {args.test_size}
    """)

    # Train + val equilibrados con lo que no está en test
    con.execute(f"""
        create temp table balanced as
        select * from (
            select *, row_number() over (partition by label order by r) as rn
            from clean
            where recommendationid not in (select recommendationid from test)
        )
        where rn <= {args.per_class}
    """)
    # val también equilibrado: las primeras reseñas de cada clase van a val y el resto a train
    n_val_per_class = int(args.per_class * args.val_frac)
    con.execute(f"create temp table val as select * from balanced where rn <= {n_val_per_class}")
    con.execute(f"create temp table train as select * from balanced where rn > {n_val_per_class}")

    cols = "recommendationid, text, label, language"
    for split in ("train", "val", "test"):
        path = OUT_DIR / f"reviews_{split}.parquet"
        con.execute(f"copy (select {cols} from {split}) to '{path}' (format parquet)")
        stats = con.execute(
            f"select count(*), round(avg(label) * 100, 1), count(distinct language) from {split}"
        ).fetchone()
        print(f"{split:5s}: {stats[0]:>6} reseñas · {stats[1]}% positivas · {stats[2]} idiomas -> {path}")


if __name__ == "__main__":
    main()
