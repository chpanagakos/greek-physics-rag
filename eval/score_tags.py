"""
Score predicted tags against the gold tags in eval/cases.jsonl.

Reports:
  Top-1 accuracy   — gold tag is the first tag predicted (the headline number)
  Any-match        — gold tag appears anywhere in the candidate list
  Mean candidates  — average number of tags emitted per case

Run:  python eval/score_tags.py
      python eval/score_tags.py --no-retrieval    (scores the ablation run)
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import CASES_PATH, EVAL  # noqa: E402


def read_jsonl(path: Path) -> list:
    if not path.exists():
        sys.exit(f"No file at {path}. Run eval/run_cases.py first.")
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-retrieval", action="store_true")
    args = parser.parse_args()

    suffix = "_noretrieval" if args.no_retrieval else ""
    preds_path = EVAL / f"predictions{suffix}.jsonl"

    gold = {c["case_id"]: c["gold_tag"] for c in read_jsonl(CASES_PATH)}
    preds = read_jsonl(preds_path)

    rows = []
    for p in preds:
        cid = p["case_id"]
        predicted = p["predicted_tags"]
        expected = gold.get(cid, "")

        top1 = bool(predicted) and predicted[0] == expected
        anym = expected in predicted

        rows.append({
            "case_id": cid,
            "gold": expected,
            "predicted": predicted,
            "top1": top1,
            "any": anym,
            "error": p.get("error"),
        })

    scored = [r for r in rows if not r["error"]]
    n = len(scored)
    if not n:
        sys.exit("No scoreable cases — every record has an error.")

    top1 = sum(r["top1"] for r in scored)
    anym = sum(r["any"] for r in scored)
    mean_candidates = sum(len(r["predicted"]) for r in scored) / n

    print(f"retrieval={'off' if args.no_retrieval else 'on'}   n={n}\n")
    print(f"{'case':6} {'top-1':6} {'any':5}  gold / predicted")
    print("-" * 70)
    for r in rows:
        if r["error"]:
            print(f"{r['case_id']:6} {'ERROR':>6}        {r['error']}")
            continue
        mark = "  ok  " if r["top1"] else " MISS "
        anymark = " yes " if r["any"] else " no  "
        print(f"{r['case_id']:6} {mark} {anymark}  {r['gold']}")
        if not r["top1"] or len(r["predicted"]) > 1:
            print(f"{'':20}predicted: {', '.join(r['predicted']) or '(none)'}")

    print("-" * 70)
    print(f"Top-1 accuracy   {top1}/{n}  ({top1 / n:.0%})")
    print(f"Any-match        {anym}/{n}  ({anym / n:.0%})")
    print(f"Mean candidates  {mean_candidates:.2f}")

    extra = sum(len(r["predicted"]) - 1 for r in scored if len(r["predicted"]) > 1)
    if extra:
        print(f"\n{extra} secondary tag(s) emitted across "
              f"{sum(1 for r in scored if len(r['predicted']) > 1)} case(s) — "
              "inspect these by hand for support.")


if __name__ == "__main__":
    main()
