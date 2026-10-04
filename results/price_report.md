# Price-prediction bench — Jev and Groq gpt-oss-20b

Two runs on the same 1,404-pair corpus. Jev run first (Groq model name was invalid that run); Groq re-run with gpt-oss-20b.

## Jev
1404 pairs (1059 positive, 345 negative). Signal = relevant>0.6 & new_info>0.5 & direction yes/no & direction_conf>=thr.

Base rate: 155 positives moved >= 1c in 30m; 52% up. A hit rate must beat 52% to mean anything.

### Ops

| model | ok | errors | p50 latency | p95 latency | total $ | $ / 1k pairs |
|---|---|---|---|---|---|---|
| jev | 1392 | 0 | 265 ms | 325 ms | 0.0320 | 0.0230 |

### Relevance on known-irrelevant pairs (lower is better)

- jev: false-positive rate 5.8% on 345 negatives

### Does the signal predict the price? (the only section that matters)

| model | conf thr | horizon | signals | moved | hit rate | avg signed move |
|---|---|---|---|---|---|---|
| jev | 0.5 | 30m | 158 | 37 | 49% | +0.19c |
| jev | 0.5 | 120m | 155 | 65 | 34% | -0.56c |
| jev | 0.7 | 30m | 132 | 29 | 52% | +0.23c |
| jev | 0.7 | 120m | 130 | 53 | 36% | -0.32c |
| jev | 0.85 | 30m | 92 | 20 | 60% | +0.45c |
| jev | 0.85 | 120m | 90 | 36 | 39% | -0.35c |

## Groq gpt-oss-20b
1404 pairs (1059 positive, 345 negative). Signal = relevant>0.6 & new_info>0.5 & direction yes/no & direction_conf>=thr.

Base rate: 155 positives moved >= 1c in 30m; 52% up. A hit rate must beat 52% to mean anything.

### Ops

| model | ok | errors | p50 latency | p95 latency | total $ | $ / 1k pairs |
|---|---|---|---|---|---|---|
| groq | 1389 | 4 | 486 ms | 760 ms | 0.6259 | 0.4506 |

### Relevance on known-irrelevant pairs (lower is better)

- groq: false-positive rate 7.0% on 344 negatives

### Does the signal predict the price? (the only section that matters)

| model | conf thr | horizon | signals | moved | hit rate | avg signed move |
|---|---|---|---|---|---|---|
| groq | 0.5 | 30m | 359 | 71 | 39% | +0.01c |
| groq | 0.5 | 120m | 352 | 131 | 31% | -0.72c |
| groq | 0.7 | 30m | 312 | 64 | 38% | +0.02c |
| groq | 0.7 | 120m | 306 | 118 | 31% | -0.75c |
| groq | 0.85 | 30m | 136 | 33 | 36% | +0.02c |
| groq | 0.85 | 120m | 134 | 58 | 34% | -0.49c |
