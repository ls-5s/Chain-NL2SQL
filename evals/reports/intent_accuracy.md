# Intent Classification Accuracy

- Dataset: `D:\Chain‑NL2SQL\evals\intent_dataset.jsonl` (50 samples)
- Confidence threshold: `0.75`
- Accuracy: **98.00%** (49/50)
- Completed accuracy (excluding provider errors): **100.00%**
- Rule hit rate: `98.00%`
- LLM fallback rate: `2.00%`
- LLM calls: `1`
- Provider errors: `1`
- Data-query false-positive rate: **0.00%**
- Mean latency: `33.78 ms`

## Per-Class Metrics

| Intent | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `data_query` | 100.00% | 100.00% | 100.00% | 20 |
| `general_chat` | 100.00% | 100.00% | 100.00% | 15 |
| `clarification` | 100.00% | 93.33% | 96.55% | 15 |

## Confusion Matrix

| Expected \ Predicted | data_query | general_chat | clarification | error |
| --- | ---: | ---: | ---: | ---: |
| `data_query` | 20 | 0 | 0 | 0 |
| `general_chat` | 0 | 15 | 0 | 0 |
| `clarification` | 0 | 0 | 14 | 1 |

## Misclassified Samples

- `业务表现怎么样？`: expected `clarification`, predicted `error`, source `error`, confidence `0.0`
