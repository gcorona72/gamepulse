"""Entrena el modelo de sentimiento (positiva / negativa) sobre reseñas de Steam.

Fine-tuning de un transformer multilingüe con Hugging Face Trainer. Usa la GPU del Mac (MPS)
si está disponible. Registra parámetros y métricas en MLflow y guarda el modelo en models/sentiment/.

Uso:
  uv run --extra gold --extra ml python -m gamepulse.ml.train_sentiment            # entrenamiento completo
  uv run --extra gold --extra ml python -m gamepulse.ml.train_sentiment --quick    # prueba rápida (~2 min)
Ver resultados:  uv run --extra ml mlflow ui --backend-store-uri sqlite:///mlflow.db
"""

import argparse
import json
import math
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import torch
from datasets import Dataset
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data" / "ml"
MODEL_DIR = ROOT / "models" / "sentiment"
LABELS = {0: "negativa", 1: "positiva"}


def load_split(name: str, limit: int | None) -> Dataset:
    df = pd.read_parquet(DATA_DIR / f"reviews_{name}.parquet")
    if limit:
        df = df.sample(n=min(limit, len(df)), random_state=42)
    return Dataset.from_pandas(df[["text", "label"]], preserve_index=False)


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1_macro": f1_score(labels, preds, average="macro"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="distilbert-base-multilingual-cased")
    parser.add_argument("--epochs", type=float, default=2)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--max-len", type=int, default=128)
    parser.add_argument("--quick", action="store_true", help="prueba con pocas reseñas")
    args = parser.parse_args()

    limit = 500 if args.quick else None
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Dispositivo: {device} · modelo: {args.model}")

    train_ds, val_ds, test_ds = (load_split(s, limit) for s in ("train", "val", "test"))
    print(f"train {len(train_ds)} · val {len(val_ds)} · test {len(test_ds)}")

    tokenizer = AutoTokenizer.from_pretrained(args.model)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=args.max_len)

    train_ds, val_ds, test_ds = (d.map(tokenize, batched=True) for d in (train_ds, val_ds, test_ds))

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=2,
        id2label=LABELS,
        label2id={v: k for k, v in LABELS.items()},
    )

    training_args = TrainingArguments(
        output_dir=str(ROOT / "models" / "checkpoints"),
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch * 2,
        weight_decay=0.01,
        warmup_steps=int(math.ceil(len(train_ds) / args.batch) * args.epochs * 0.1),
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        logging_steps=50,
        report_to=["mlflow"],
        seed=42,
    )

    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("gamepulse-sentiment")
    with mlflow.start_run(run_name=f"{args.model.split('/')[-1]}{'-quick' if args.quick else ''}"):
        mlflow.log_params({"max_len": args.max_len, "device": device, "n_train": len(train_ds)})

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_ds,
            eval_dataset=val_ds,
            processing_class=tokenizer,
            data_collator=DataCollatorWithPadding(tokenizer),
            compute_metrics=compute_metrics,
        )
        trainer.train()

        # Evaluación final en test (distribución real, ~77 % positivas)
        pred = trainer.predict(test_ds)
        y_true = pred.label_ids
        y_pred = np.argmax(pred.predictions, axis=-1)
        acc = accuracy_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred, average="macro")
        cm = confusion_matrix(y_true, y_pred)
        report = classification_report(y_true, y_pred, target_names=list(LABELS.values()), digits=3)

        mlflow.log_metrics({"test_accuracy": acc, "test_f1_macro": f1})
        mlflow.log_text(report, "test_report.txt")
        mlflow.log_dict({"confusion_matrix": cm.tolist(), "labels": list(LABELS.values())}, "confusion_matrix.json")

        print("\n=== TEST ===")
        print(report)
        print("Matriz de confusión (filas = real, columnas = predicho) [negativa, positiva]:")
        print(cm)

        if not args.quick:
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            trainer.save_model(str(MODEL_DIR))
            tokenizer.save_pretrained(str(MODEL_DIR))
            (MODEL_DIR / "metrics.json").write_text(json.dumps({"test_accuracy": acc, "test_f1_macro": f1}, indent=2))
            print(f"Modelo guardado en {MODEL_DIR}")


if __name__ == "__main__":
    main()
