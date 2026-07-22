"""
Generate eval/cases.jsonl from the demo examples in examples.py.

Run once:  python eval/make_cases.py

Writes each example as a case record with gold_tag left blank — you fill those
in by hand from taxonomy.json. Refuses to overwrite an existing case file.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from examples import EXAMPLES  # noqa: E402
from paths import CASES_PATH  # noqa: E402


def main():
    if CASES_PATH.exists():
        sys.exit(f"{CASES_PATH} already exists — refusing to overwrite.")

    CASES_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(CASES_PATH, "w", encoding="utf-8") as f:
        for i, (problem, attempt) in enumerate(EXAMPLES, start=1):
            case = {
                "case_id": f"c{i:03d}",
                "problem_text": problem,
                "student_attempt": attempt,
                "gold_tag": "",  # fill in by hand from taxonomy.json
                "tag_source": "self",
                "attempt_source": "gemini",
            }
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    print(f"Wrote {len(EXAMPLES)} cases to {CASES_PATH}")
    print("Next: fill in gold_tag for each line from taxonomy.json.")


if __name__ == "__main__":
    main()
