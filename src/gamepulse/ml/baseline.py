"""Baseline clásico: TF-IDF (n-gramas de caracteres) + regresión logística.

Sirve de referencia para justificar el transformer: mismo train y mismo test.
Uso:  uv run --extra ml python -m gamepulse.ml.baseline
"""

from pathlib import Path

import mlflow
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data" / "ml"


def main() -> None:
    train = pd.concat([pd.read_parquet(DATA_DIR / f"reviews_{s}.parquet") for s in ("train", "val")])
    test = pd.read_parquet(DATA_DIR / "reviews_test.parquet")

    # n-gramas de caracteres: funcionan en cualquier idioma (chino, ruso...) sin tokenizador específico
    model = make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3, max_features=200_000, sublinear_tf=True),
        LogisticRegression(max_iter=2000, C=2.0),
    )
    model.fit(train["text"], train["label"])
    y_pred = model.predict(test["text"])

    acc = accuracy_score(test["label"], y_pred)
    f1 = f1_score(test["label"], y_pred, average="macro")
    report = classification_report(test["label"], y_pred, target_names=["negativa", "positiva"], digits=3)

    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("gamepulse-sentiment")
    with mlflow.start_run(run_name="baseline-tfidf-logreg"):
        mlflow.log_params({"model": "tfidf_char_2-5 + logreg", "n_train": len(train)})
        mlflow.log_metrics({"test_accuracy": acc, "test_f1_macro": f1})
        mlflow.log_text(report, "test_report.txt")

    print("=== TEST (baseline TF-IDF + LogReg) ===")
    print(report)
    print(confusion_matrix(test["label"], y_pred))


if __name__ == "__main__":
    main()
