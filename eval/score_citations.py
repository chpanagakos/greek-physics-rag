"""
Citation validity: is every cited chunk ID one that retrieval actually
returned for that case?

A cited ID absent from the retrieved set is a FABRICATED citation — the
model invented provenance. This is validity (the ID is real and was on the
table), not precision (the chunk supports the claim); precision requires
human judgment and is tracked separately.

Also reports, per case, which retrieved chunks were cited vs ignored, and
citation "coverage" of the hand-labelled gold chunks — of the gold chunks
that WERE retrieved, how many did the model choose to cite?

Reads predictions.jsonl only. No API calls.

Run:  python eval/score_citations.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import CASES_PATH, EVAL  # noqa: E402


def read_jsonl(path: Path) -> list:
    if not path.exists():
        sys.exit(f"No file at {path}.")
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def main():
    cases = {c["case_id"]: c for c in read_jsonl(CASES_PATH)}
    preds = [p for p in read_jsonl(EVAL / "predictions.jsonl") if not p.get("error")]

    n = len(preds)
    total_cited = 0
    total_fabricated = 0
    gold_retrieved_total = 0
    gold_cited_total = 0

    print(f"n={n} cases (retrieval on)\n")
    print(f"{'case':6} {'cited':>6} {'fabricated':>11}  detail")
    print("-" * 72)

    for p in preds:
        cid = p["case_id"]
        retrieved = set(p["retrieved_chunk_ids"])
        cited = p["cited_chunk_ids"]
        gold = set(cases.get(cid, {}).get("gold_chunk_ids") or [])

        fabricated = [c for c in cited if c not in retrieved]
        gold_retrieved = gold & retrieved
        gold_cited = gold_retrieved & set(cited)

        total_cited += len(cited)
        total_fabricated += len(fabricated)
        gold_retrieved_total += len(gold_retrieved)
        gold_cited_total += len(gold_cited)

        detail = []
        if fabricated:
            detail.append(f"FABRICATED: {', '.join(fabricated)}")
        if gold_retrieved and not gold_cited:
            detail.append(f"gold retrieved but NOT cited: {', '.join(sorted(gold_retrieved))}")
        print(f"{cid:6} {len(cited):>6} {len(fabricated):>11}  {'; '.join(detail)}")

    print("-" * 72)
    valid = total_cited - total_fabricated
    print(f"Citation validity   {valid}/{total_cited} "
          f"({valid / total_cited:.0%}) cited IDs were actually retrieved")
    if gold_retrieved_total:
        print(f"Gold coverage       {gold_cited_total}/{gold_retrieved_total} "
              f"({gold_cited_total / gold_retrieved_total:.0%}) of retrieved gold "
              "chunks were cited")

    print(
        "\nNote: validity is not enforced anywhere in code — parse_response "
        "validates\ntags against the closed taxonomy but never checks cited IDs "
        "against the\nretrieved set. If validity is 100% here, that is prompt "
        "compliance, not a\nguarantee. Candidate for the pytest layer."
    )


if __name__ == "__main__":
    main()
