from __future__ import annotations

import json
from pathlib import Path

from app.schemas.domain import QueryIntent
from scripts.evaluate_intent import build_report, load_dataset, render_markdown


ROOT = Path(__file__).resolve().parents[2]


def test_intent_dataset_has_expected_balanced_counts() -> None:
    records = load_dataset(ROOT / "evals" / "intent_dataset.jsonl")

    assert len(records) == 50
    assert {category: sum(item["category"] == category for item in records) for category in {"clear_data", "general_chat", "ambiguous"}} == {
        "clear_data": 20,
        "general_chat": 15,
        "ambiguous": 15,
    }


def test_report_calculates_accuracy_confusion_and_data_false_positives() -> None:
    results = [
        {"expected_intent": QueryIntent.DATA_QUERY.value, "predicted_intent": QueryIntent.DATA_QUERY.value, "source": "rule", "confidence": 0.96, "classification_valid": True, "latency_ms": 1.0, "question": "q1", "category": "clear_data", "reason": "ok", "error_type": None},
        {"expected_intent": QueryIntent.GENERAL_CHAT.value, "predicted_intent": QueryIntent.DATA_QUERY.value, "source": "llm", "confidence": 0.8, "classification_valid": True, "latency_ms": 3.0, "question": "q2", "category": "general_chat", "reason": "wrong", "error_type": None},
        {"expected_intent": QueryIntent.CLARIFICATION.value, "predicted_intent": QueryIntent.CLARIFICATION.value, "source": "llm", "confidence": 0.5, "classification_valid": False, "latency_ms": 5.0, "question": "q3", "category": "ambiguous", "reason": "low", "error_type": None},
    ]

    report = build_report(results)

    assert report["accuracy"] == 0.6667
    assert report["rule_hit_rate"] == 0.3333
    assert report["llm_fallback_rate"] == 0.6667
    assert report["data_query_false_positive_count"] == 1
    assert report["data_query_false_positive_rate"] == 1 / 2
    assert report["confusion_matrix"]["general_chat"]["data_query"] == 1


def test_markdown_report_is_renderable(tmp_path: Path) -> None:
    report = build_report([])
    output = render_markdown(report, Path("dataset.jsonl"), 0.75)

    assert "# Intent Classification Accuracy" in output
    assert "Confusion Matrix" in output
    (tmp_path / "report.md").write_text(output, encoding="utf-8")
    json.dumps(report)
