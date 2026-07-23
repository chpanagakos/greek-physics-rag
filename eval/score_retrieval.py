"""
Retrieval metrics: how well does retrieval surface the gold chunks?

No LLM anywhere in this file. It compares the chunk IDs retrieval returned
against the gold_chunk_ids labelled by hand, and reports:

  Recall@k    fraction of cases with AT LEAST ONE gold chunk in the top k
  Full@k      fraction of cases with ALL gold chunks in the top k
  MRR         mean reciprocal rank of the first gold chunk

Two Recall variants because most cases have >1 gold chunk: Recall@k answers
"did retrieval find something to ground the diagnosis in", Full@k answers
"did it find everything a tutor would cite". They measure different things
and the gap between them is informative.

Reads retrieved_chunk_ids from predictions.jsonl, so it needs no API calls
and no Qdrant lock — it re-scores a run that already happened.

Run:  python eval/score_retrieval.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import CASES_PATH, EVAL  # noqa: E402

KS = (1, 3, 5)


def read_jsonl(path: Path) -> list:
    if not path.exists():
        sys.exit(f"No file at {path}.")
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def first_gold_rank(retrieved: list, gold: set):
    """1-based rank of the first gold chunk, or None if absent."""
    for i, cid in enumerate(retrieved, start=1):
        if cid in gold:
            return i
    return None


def main():
    cases = {c["case_id"]: c for c in read_jsonl(CASES_PATH)}
    preds = read_jsonl(EVAL / "predictions.jsonl")

    rows = []
    for p in preds:
        case = cases.get(p["case_id"])
        if case is None or case.get("gold_chunk_ids") is None:
            continue
        if p.get("error"):
            continue

        gold = set(case["gold_chunk_ids"])
        retrieved = p["retrieved_chunk_ids"]
        if not gold or not retrieved:
            continue

        rank = first_gold_rank(retrieved, gold)
        rows.append({
            "case_id": p["case_id"],
            "gold": case["gold_chunk_ids"],
            "retrieved": retrieved,
            "rank": rank,
            "found": sorted(gold & set(retrieved)),
            "missing": sorted(gold - set(retrieved)),
            "pool_miss": bool(case.get("pool_miss")),
        })

    n = len(rows)
    if not n:
        sys.exit("No scoreable cases: label gold_chunk_ids first.")

    k_max = max(len(r["retrieved"]) for r in rows)
    print(f"n={n} cases, retrieval depth k={k_max}\n")

    print(f"{'case':6} {'rank':>5}  {'found':>5}  gold chunks")
    print("-" * 72)
    for r in rows:
        rank = r["rank"] if r["rank"] else "—"
        found = f"{len(r['found'])}/{len(r['gold'])}"
        flag = "  POOL MISS" if r["pool_miss"] else ""
        print(f"{r['case_id']:6} {str(rank):>5}  {found:>5}  {', '.join(r['gold'])}{flag}")
        if r["missing"]:
            print(f"{'':21}not retrieved: {', '.join(r['missing'])}")

    print("-" * 72)
    for k in KS:
        if k > k_max:
            continue
        hit = sum(1 for r in rows if r["rank"] is not None and r["rank"] <= k)
        full = sum(
            1 for r in rows
            if set(r["gold"]) <= set(r["retrieved"][:k])
        )
        print(f"Recall@{k}  {hit}/{n} ({hit / n:.0%})    "
              f"Full@{k}  {full}/{n} ({full / n:.0%})")

    mrr = sum(1 / r["rank"] for r in rows if r["rank"]) / n
    print(f"MRR       {mrr:.3f}")

    missed = [r["case_id"] for r in rows if r["rank"] is None]
    if missed:
        print(f"\nNo gold chunk retrieved at all: {', '.join(missed)}")


if __name__ == "__main__":
    main()
