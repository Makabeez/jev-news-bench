#!/usr/bin/env python3
"""
collect.py — build a labeled (headline, market, price move) dataset. No API keys needed.

  Polymarket Gamma  -> top active YES/NO markets by 24h volume
  Google News RSS   -> headlines per market (last N hours, keyword query)
  Polymarket CLOB   -> 1-min YES price history -> move at +30m / +2h after publish time

Writes pairs.jsonl. Positives = keyword-retrieved (headline, market) pairs.
Negatives = the same headlines paired with a random unrelated market (truth: irrelevant).
"""
import argparse, bisect, hashlib, json, random, re, time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import requests

GAMMA = "https://gamma-api.polymarket.com/markets"
CLOB_HIST = "https://clob.polymarket.com/prices-history"
GNEWS = "https://news.google.com/rss/search"
UA = {"User-Agent": "jev-news-bench/0.1"}

STOP = set("""will the a an of in on by to for and or is be at as with from this that than
before after end yes no who what which when does do did win wins price above below between
market hit reach next most more less over under least new first""".split())
EXCLUDE = re.compile(r"up or down|updown|\bvs\.?\b|o/u|spread|game \d|map \d|set \d|total", re.I)


def get_markets(n, min_vol):
    out, offset = [], 0
    while len(out) < n and offset < 1500:
        r = requests.get(GAMMA, params={"active": "true", "closed": "false", "order": "volume24hr",
                                        "ascending": "false", "limit": 100, "offset": offset},
                         headers=UA, timeout=20)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        for m in batch:
            try:
                toks = json.loads(m.get("clobTokenIds") or "[]")
                outs = [o.lower() for o in json.loads(m.get("outcomes") or "[]")]
            except (ValueError, TypeError):
                continue
            q = m.get("question") or ""
            if len(toks) != 2 or outs != ["yes", "no"] or EXCLUDE.search(q + " " + (m.get("slug") or "")):
                continue
            if float(m.get("volume24hr") or 0) < min_vol:
                continue
            out.append({"market_id": m["id"], "slug": m.get("slug"), "question": q,
                        "yes_token": toks[0], "end": m.get("endDate"),
                        "vol24h": round(float(m.get("volume24hr") or 0))})
        offset += 100
    return out[:n]


def key_terms(q):
    words = re.findall(r"[A-Za-z][A-Za-z.'&-]+", q)
    terms = []
    for w in words:
        w = w.strip(".'")
        if w[:1].isupper() and w.lower() not in STOP and len(w) >= 3 and w not in terms:
            terms.append(w)
    if not terms:
        terms = [w for w in words if w.lower() not in STOP and len(w) >= 5][:2]
    return terms[:3]


def headlines(terms, hours, cap):
    q = " ".join(terms) + f" when:{max(1, hours // 24)}d"
    try:
        r = requests.get(GNEWS, params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                         headers=UA, timeout=20)
        root = ET.fromstring(r.content)
    except (requests.RequestException, ET.ParseError):
        return []
    out = []
    for it in root.iter("item"):
        title, pub = it.findtext("title") or "", it.findtext("pubDate")
        src = it.findtext("source") or ""
        if not pub:
            continue
        # Google appends " - Source" to titles; strip it
        if src and title.endswith(" - " + src):
            title = title[: -len(src) - 3]
        out.append({"headline": title.strip(), "source": src,
                    "ts": int(parsedate_to_datetime(pub).timestamp())})
    return out[:cap]


def history(token, start, end):
    try:
        r = requests.get(CLOB_HIST, params={"market": token, "startTs": start, "endTs": end, "fidelity": 1},
                         headers=UA, timeout=30)
        h = r.json().get("history", []) if r.status_code == 200 else []
    except (requests.RequestException, ValueError):
        h = []
    h.sort(key=lambda x: x["t"])
    return [x["t"] for x in h], [x["p"] for x in h]


def price_at(ts_list, px_list, ts):
    i = bisect.bisect_right(ts_list, ts) - 1
    if i < 0 or ts - ts_list[i] > 1800:  # no print within 30 min before -> unknown
        return None
    return px_list[i]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", type=int, default=40)
    ap.add_argument("--min-vol", type=float, default=20000)
    ap.add_argument("--hours", type=int, default=72)
    ap.add_argument("--per-market", type=int, default=15)
    ap.add_argument("--neg-ratio", type=float, default=0.3)
    ap.add_argument("--out", default="pairs.jsonl")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    random.seed(a.seed)

    now = int(time.time())
    start = now - a.hours * 3600 - 3600
    markets = get_markets(a.markets, a.min_vol)
    print(f"{len(markets)} markets")

    rows, hist = [], {}
    for m in markets:
        terms = key_terms(m["question"])
        if not terms:
            continue
        hs = headlines(terms, a.hours, a.per_market)
        hist[m["market_id"]] = history(m["yes_token"], start, now)
        print(f"  {len(hs):>3} headlines | {' '.join(terms):<35} | {m['question'][:70]}")
        for h in hs:
            if h["ts"] < start:
                continue
            rows.append((h, m))
        time.sleep(1.0)

    by_id = {m["market_id"]: m for m in markets}
    pairs, seen = [], set()

    def label(h, m, neg):
        ts_l, px_l = hist.get(m["market_id"], ([], []))
        p0 = price_at(ts_l, px_l, h["ts"])
        p30 = price_at(ts_l, px_l, h["ts"] + 1800) if h["ts"] + 1800 <= now else None
        p120 = price_at(ts_l, px_l, h["ts"] + 7200) if h["ts"] + 7200 <= now else None
        return {"pair_id": f"{m['market_id']}:{h['ts']}:{hashlib.sha1(h['headline'].encode()).hexdigest()[:8]}",
                "headline": h["headline"], "source": h["source"], "ts": h["ts"],
                "market_id": m["market_id"], "question": m["question"], "slug": m["slug"], "end": m["end"],
                "p0": p0,
                "move30": round(p30 - p0, 4) if p0 is not None and p30 is not None else None,
                "move120": round(p120 - p0, 4) if p0 is not None and p120 is not None else None,
                "negative": neg}

    for h, m in rows:
        key = (m["market_id"], h["headline"].lower())
        if key in seen:
            continue
        seen.add(key)
        pairs.append(label(h, m, False))
        if random.random() < a.neg_ratio and len(by_id) > 1:
            other = random.choice([x for x in markets if x["market_id"] != m["market_id"]])
            pairs.append(label(h, other, True))

    with open(a.out, "w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")
    pos = [p for p in pairs if not p["negative"]]
    lab = [p for p in pos if p["move30"] is not None]
    print(f"\n{len(pairs)} pairs -> {a.out}  ({len(pos)} positive, {len(pairs) - len(pos)} negative, "
          f"{len(lab)} positives with +30m price label)")


if __name__ == "__main__":
    main()
