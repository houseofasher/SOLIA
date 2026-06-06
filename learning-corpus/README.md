# Aureon learning corpus (auto-synced)

**Exported:** 2026-06-06T10:25:56.879894+00:00

Full export of everything Aureon has learned — not just self-inquiry.

## Summary

- **Documents (full corpus):** 462
- **Labels:** 462
- **Graduated grade steps:** 150
- **In progress:** 0
- **Training runs:** 134
- **Benchmarks:** 450
- **Preference pairs (RLHF):** 0

## Files

| File | Contents |
|------|----------|
| `learned_corpus.jsonl` | Documents + labels + topics (main export) |
| `documents.jsonl` | All collected/verified text Aureon ingested |
| `document_labels.json` | Teacher labels per document |
| `grade_progress.json` | Full grade ladder state per micro-topic |
| `graduation_summary.json` | Passed graduations with train accuracy |
| `training_runs.json` | Model training history |
| `benchmarks.json` | Evaluator benchmark scores |
| `preference_pairs.json` | Reward/RLHF preference data |
| `pipeline_events.json` | Recent pipeline events |
| `models/` | Trained classifier weights (JSON) |
| `self_inquiry.jsonl` | Learning reflections — document excerpts + cycle metrics |
| `snapshot.json` | Live brain + auto-learn status |

Auto-generated on Railway. Secrets and audit logs are never included.
