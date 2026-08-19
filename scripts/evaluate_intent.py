"""Evaluate the production intent gate against a fixed labeled JSONL dataset."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Callable

# Evaluation questions must not be sent to LangSmith by default.
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGCHAIN_TRACING", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.settings import get_settings
from app.graph.intent_node import make_intent_gate_node
from app.llm.factory import create_openai_client
from app.schemas.domain import QueryIntent

LABELS = tuple(intent.value for intent in QueryIntent)
EXPECTED_CATEGORY_COUNTS = {"clear_data": 20, "general_chat": 15, "ambiguous": 15}


def load_dataset(path: Path) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(records) != 50:
        raise ValueError(f"Expected 50 labeled records, found {len(records)}.")
    categories = Counter(record.get("category") for record in records)
    if dict(categories) != EXPECTED_CATEGORY_COUNTS:
        raise ValueError(f"Unexpected category counts: {dict(categories)}")
    for index, record in enumerate(records, start=1):
        if not all(record.get(field) for field in ("question", "expected_intent", "category", "reason")):
            raise ValueError(f"Record {index} is missing a required field.")
        if record["expected_intent"] not in LABELS:
            raise ValueError(f"Record {index} has an unknown expected intent.")
    return records


def classify_records(
    records: list[dict[str, Any]],
    classifier: Callable[[str], dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for record in records:
        started = time.perf_counter()
        try:
            outcome = classifier(record["question"])
            predicted = outcome.get("intent")
            predicted = predicted.value if isinstance(predicted, QueryIntent) else predicted
            result = {
                "question": record["question"],
                "expected_intent": record["expected_intent"],
                "predicted_intent": predicted if predicted in LABELS else None,
                "category": record["category"],
                "source": outcome.get("intent_source"),
                "confidence": outcome.get("intent_confidence"),
                "reason": outcome.get("intent_reason"),
                "classification_valid": outcome.get("intent_classification_valid", False),
                "error_type": None,
            }
        except Exception as error:  # Evaluation must continue after a single provider failure.
            result = {
                "question": record["question"],
                "expected_intent": record["expected_intent"],
                "predicted_intent": None,
                "category": record["category"],
                "source": "error",
                "confidence": 0.0,
                "reason": None,
                "classification_valid": False,
                "error_type": type(error).__name__,
            }
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        results.append(result)
    return results


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    correct = sum(item["expected_intent"] == item["predicted_intent"] for item in results)
    predictions = [item["predicted_intent"] for item in results]
    expected = [item["expected_intent"] for item in results]
    metrics: dict[str, dict[str, float]] = {}
    for label in LABELS:
        true_positive = sum(actual == label and predicted == label for actual, predicted in zip(expected, predictions))
        predicted_count = sum(predicted == label for predicted in predictions)
        expected_count = sum(actual == label for actual in expected)
        precision = true_positive / predicted_count if predicted_count else 0.0
        recall = true_positive / expected_count if expected_count else 0.0
        metrics[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(_f1(precision, recall), 4),
            "support": expected_count,
        }

    confusion: dict[str, dict[str, int]] = {
        actual: {predicted: 0 for predicted in (*LABELS, "error")} for actual in LABELS
    }
    for item in results:
        predicted = item["predicted_intent"] or "error"
        confusion[item["expected_intent"]][predicted] += 1

    non_data = [item for item in results if item["expected_intent"] != QueryIntent.DATA_QUERY.value]
    false_positive_count = sum(item["predicted_intent"] == QueryIntent.DATA_QUERY.value for item in non_data)
    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "per_class": metrics,
        "confusion_matrix": confusion,
        "rule_hit_rate": round(sum(item["source"] == "rule" for item in results) / total, 4) if total else 0.0,
        "llm_fallback_rate": round(sum(item["source"] in {"llm", "error"} for item in results) / total, 4) if total else 0.0,
        "provider_error_count": sum(item["source"] == "error" for item in results),
        "llm_call_count": sum(item["source"] in {"llm", "error"} for item in results),
        "invalid_or_low_confidence_count": sum(item["source"] == "llm" and not item["classification_valid"] for item in results),
        "data_query_false_positive_count": false_positive_count,
        "data_query_false_positive_rate": round(false_positive_count / len(non_data), 4) if non_data else 0.0,
        "mean_latency_ms": round(mean(item["latency_ms"] for item in results), 2) if results else 0.0,
        "completed_accuracy": round(
            sum(item["expected_intent"] == item["predicted_intent"] for item in results if item["source"] != "error")
            / sum(item["source"] != "error" for item in results),
            4,
        ) if any(item["source"] != "error" for item in results) else 0.0,
        "errors": [item for item in results if item["expected_intent"] != item["predicted_intent"]],
    }


def render_markdown(report: dict[str, Any], dataset_path: Path, threshold: float) -> str:
    lines = [
        "# Intent Classification Accuracy",
        "",
        f"- Dataset: `{dataset_path}` ({report['total']} samples)",
        f"- Confidence threshold: `{threshold}`",
        f"- Accuracy: **{report['accuracy']:.2%}** ({report['correct']}/{report['total']})",
        f"- Completed accuracy (excluding provider errors): **{report['completed_accuracy']:.2%}**",
        f"- Rule hit rate: `{report['rule_hit_rate']:.2%}`",
        f"- LLM fallback rate: `{report['llm_fallback_rate']:.2%}`",
        f"- LLM calls: `{report['llm_call_count']}`",
        f"- Provider errors: `{report['provider_error_count']}`",
        f"- Data-query false-positive rate: **{report['data_query_false_positive_rate']:.2%}**",
        f"- Mean latency: `{report['mean_latency_ms']} ms`",
        "",
        "## Per-Class Metrics",
        "",
        "| Intent | Precision | Recall | F1 | Support |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label, values in report["per_class"].items():
        lines.append(
            f"| `{label}` | {values['precision']:.2%} | {values['recall']:.2%} | "
            f"{values['f1']:.2%} | {values['support']} |"
        )
    lines.extend(["", "## Confusion Matrix", "", "| Expected \\ Predicted | " + " | ".join((*LABELS, "error")) + " |", "| --- | " + " | ".join("---:" for _ in (*LABELS, "error")) + " |"])
    for actual in LABELS:
        lines.append("| `" + actual + "` | " + " | ".join(str(report["confusion_matrix"][actual][label]) for label in (*LABELS, "error")) + " |")
    lines.extend(["", "## Misclassified Samples", ""])
    if not report["errors"]:
        lines.append("No misclassified samples.")
    else:
        for item in report["errors"]:
            lines.append(
                f"- `{item['question']}`: expected `{item['expected_intent']}`, "
                f"predicted `{item['predicted_intent'] or 'error'}`, source `{item['source']}`, "
                f"confidence `{item['confidence']}`"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "evals" / "intent_dataset.jsonl")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "evals" / "reports")
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--timeout", type=float, default=None)
    args = parser.parse_args()

    settings = get_settings()
    threshold = args.threshold if args.threshold is not None else settings.intent_confidence_threshold
    timeout = args.timeout if args.timeout is not None else float(settings.query_timeout_seconds)
    if not 0.0 < threshold <= 1.0:
        raise SystemExit("--threshold must be between 0 and 1.")
    records = load_dataset(args.dataset)
    llm_client = create_openai_client(settings)
    gate = make_intent_gate_node(llm_client, timeout, threshold)
    results = classify_records(records, lambda question: gate({"question": question}))
    report = build_report(results)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "intent_accuracy.json").write_text(
        json.dumps({"config": {"threshold": threshold, "timeout_seconds": timeout}, **report}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "intent_accuracy.md").write_text(render_markdown(report, args.dataset, threshold), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("total", "accuracy", "completed_accuracy", "rule_hit_rate", "llm_fallback_rate", "provider_error_count", "data_query_false_positive_rate", "mean_latency_ms")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
