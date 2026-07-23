"""
H1 — query construction experiment: problem-only vs problem+attempt.

Everything is held fixed (corpus, embeddings, Qdrant, k) except the query
string. Scores both configurations against the hand-labelled gold chunks
and reports Recall@k and MRR side by side.

Reads eval/pools.json, which label_tool.py cached during labelling: for
every case, the top-10 chunk ranks under BOTH query configurations. So
this experiment costs nothing to run — the retrieval already happened.

Caveat printed with the results: gold chunks were labelled from the pooled
union of these two configurations, so neither side can be charged with
missing a chunk outside both top-10s. The comparison BETWEEN them is fair;
the absolute numbers inherit the pooling floor.

Run:  python eval/score_query_construction.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import CASES_PATH, POOLS_PATH  # noqa: E402

KS = (1, 3, 5, 10)
CONFIGS = {
    "problem only": "rank_problem",
    "problem + attempt": "rank_both",
}


def read_cases() -> list:
    lines = CASES_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def gold_ranks(pool_ranks: dict, gold: list) -> list:
    """Ranks of the gold chunks under one configuration (unranked -> None)."""
    return [pool_ranks.get(g) for g in gold]


def main():
    if not POOLS_PATH.exists():
        sys.exit(f"No pool cache at {POOLS_PATH}. Run eval/label_tool.py first.")

    pools = json.loads(POOLS_PATH.read_text(encoding="utf-8"))
    cases = [c for c in read_cases() if c.get("gold_chunk_ids")]
    n = len(cases)
    if not n:
        sys.exit("No cases with gold_chunk_ids.")

    # Per-case detail table.
    print(f"n={n} cases — rank of each gold chunk under each query configuration")
    print(f"{'case':6} {'gold chunk':14} {'problem':>9} {'prob+att':>9}")
    print("-" * 44)
    for case in cases:
        cid = case["case_id"]
        pool = pools.get(cid)
        if pool is None:
            print(f"{cid:6} (no pool cached)")
            continue
        for g in case["gold_chunk_ids"]:
            rp = pool["rank_problem"].get(g, "—")
            rb = pool["rank_both"].get(g, "—")
            marker = ""
            if rp != rb:
                better = "problem" if (rb == "—" or (rp != "—" and rp < rb)) else "prob+att"
                marker = f"   <- {better} better"
            print(f"{cid:6} {g:14} {str(rp):>9} {str(rb):>9}{marker}")

    # Aggregate metrics per configuration.
    print("\n" + "=" * 44)
    print(f"{'metric':12}" + "".join(f"{name:>20}" for name in CONFIGS))
    print("-" * 52)

    scores = {}
    for name, key in CONFIGS.items():
        per_case_first = []
        for case in cases:
            pool = pools.get(case["case_id"])
            if pool is None:
                continue
            ranks = [r for r in gold_ranks(pool[key], case["gold_chunk_ids"]) if r]
            per_case_first.append(min(ranks) if ranks else None)
        scores[name] = per_case_first

    for k in KS:
        row = f"Recall@{k:<5}"
        for name in CONFIGS:
            hit = sum(1 for r in scores[name] if r is not None and r <= k)
            row += f"{hit}/{n} ({hit / n:.0%})".rjust(20)
        print(row)

    row = f"{'MRR':12}"
    for name in CONFIGS:
        mrr = sum(1 / r for r in scores[name] if r) / n
        row += f"{mrr:.3f}".rjust(20)
    print(row)

    print(
        "\nCaveat: gold labels were pooled from the union of these two "
        "configurations,\nso the comparison between them is fair but the "
        "absolute numbers inherit\nthe pooling floor (see NOTES.md)."
    )


if __name__ == "__main__":
    main()
