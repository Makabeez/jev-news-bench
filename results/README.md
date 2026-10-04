# results

Outputs from the run reported in the main README (corpus collected 2026-09-29, runs 2026-10-03/04).

| file | what |
|---|---|
| `injection_report.md` | steer rates, bootstrap CIs, McNemar p, manufactured relevance — 450 pairs × 7 arms × 2 models |
| `gate_report.md` | confidence-gate survival, honest retention and lift per threshold |
| `price_report.md` | price-prediction hit rates, latency, cost |
| `injection_raw.jsonl` | every model answer: `{model, arm, pair_id, answer}` |

Pair IDs are `market_id:unix_ts:sha1(headline)[:8]`. The headline text itself is not redistributed.
