"""
Run every case in eval/cases.jsonl through the pipeline and record what the
system produced. Scoring happens separately.

One record per case, capturing everything both measurements need:
  predicted_tags       -> tag accuracy
  retrieved_chunk_ids  -> Recall@k and MRR, once gold_chunk_ids exist
  cited_chunk_ids      -> citation validity

Appends and skips cases already recorded, so an interrupted run resumes
without re-spending API calls.

Embedded Qdrant takes an exclusive lock, so close app.py before running.

Run:  python eval/run_cases.py
      python eval/run_cases.py --no-retrieval     (ablation condition)
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import CASES_PATH, EVAL  # noqa: E402
from prompt import QuotaExceededError, diagnose  # noqa: E402
from retrieve import retrieve  # noqa: E402

SLEEP_SECONDS = 2.0   # spacing between API calls
RETRIEVAL_K = 5       # matches retrieve.DEFAULT_K; recorded per run


def load_cases() -> list:
    lines = CASES_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def load_done(path: Path) -> set:
    if not path.exists():
        return set()
    return {
        json.loads(line)["case_id"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def run_one(case: dict, use_retrieval: bool) -> dict:
    """Retrieve, diagnose, and flatten the result into a record."""
    chunks = retrieve(case["problem_text"], RETRIEVAL_K) if use_retrieval else []
    result = diagnose(
        case["problem_text"],
        case["student_attempt"],
        chunks,
        use_retrieval=use_retrieval,
    )
    return {
        "predicted_tags": result["tags"],
        "cited_chunk_ids": result["cited_chunk_ids"],
        "retrieved_chunk_ids": [c["chunk_id"] for c in chunks],
        "justification": result["justification"],
        "error": None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-retrieval", action="store_true",
                        help="ablation condition: no retrieved context in the prompt")
    args = parser.parse_args()

    use_retrieval = not args.no_retrieval
    suffix = "" if use_retrieval else "_noretrieval"
    out_path = EVAL / f"predictions{suffix}.jsonl"

    cases = load_cases()
    done = load_done(out_path)

    print(f"retrieval={'on' if use_retrieval else 'off'} -> {out_path.name}")
    print(f"{len(cases)} cases, {len(done)} already recorded\n")

    for case in cases:
        cid = case["case_id"]
        if cid in done:
            print(f"{cid}  skipped")
            continue

        try:
            record = run_one(case, use_retrieval)
        except QuotaExceededError:
            print(f"{cid}  QUOTA EXHAUSTED — stopping. Rerun later to resume.")
            break
        except Exception as exc:            # noqa: BLE001 — record and continue
            record = {
                "predicted_tags": [],
                "cited_chunk_ids": [],
                "retrieved_chunk_ids": [],
                "justification": "",
                "error": f"{type(exc).__name__}: {exc}",
            }

        record = {"case_id": cid, "use_retrieval": use_retrieval, **record}

        with open(out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        if record["error"]:
            print(f"{cid}  ERROR  {record['error']}")
        else:
            print(f"{cid}  {record['predicted_tags']}")

        time.sleep(SLEEP_SECONDS)

    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
