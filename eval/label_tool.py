"""
Gold-chunk labelling tool (internal scaffold — not part of the shipped app).

Workflow per case:
  1. Retrieve top-K for both query configurations (problem only / problem + attempt).
  2. Pool the union of those hits.
  3. Present the pooled chunk TEXTS in randomised order, with ranks and chunk_ids hidden.
  4. You tick the ones that are gold under the frozen rule.
  5. Save writes gold_chunk_ids back into eval/cases.jsonl.

Blinding is deliberate: judging text without seeing rank or chunk_id keeps the
labels independent of the system being measured. Ranks are revealable after saving.

Run:  python eval/label_tool.py
"""

import json
import random
from pathlib import Path

import gradio as gr

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

REPO = Path(__file__).resolve().parent.parent
CASES_PATH = REPO / "eval" / "cases.jsonl"
CHUNKS_PATH = REPO / "data" / "chunks.jsonl"      # <-- CHECK THIS PATH
POOLS_PATH = REPO / "eval" / "pools.json"          # cache so restarts are fast
POOL_K = 10

# Keep this string identical to the rule frozen in SPEC.md.
LABELLING_RULE = (
    "A chunk is GOLD if a tutor would need to cite it to justify THIS diagnosis. "
    "The chunk stating the principle the student violated is gold. "
    "A chunk stating the principle the student should have used instead is NOT gold. "
    "A chunk on an adjacent topic the student merely mentioned is NOT gold. "
    "Expect 1-3 gold chunks. If you are marking 5, the rule is being applied too loosely."
)

# ---------------------------------------------------------------------------
# ADAPTER — the only section you should need to edit.
# ---------------------------------------------------------------------------

def load_chunks() -> dict:
    """Return {chunk_id: text} for all 62 chunks."""
    chunks = {}
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            chunks[str(rec["chunk_id"])] = rec["text"]   # <-- CHECK FIELD NAMES
    return chunks


def retrieve_topk(query: str, k: int = POOL_K) -> list:
    """Return a list of chunk_id strings in rank order (best first)."""
    from retrieve import search            # <-- CHECK MODULE + FUNCTION NAME
    hits = search(query, top_k=k)          # <-- CHECK ARG NAME
    return [_hit_to_id(h) for h in hits]


def _hit_to_id(hit) -> str:
    """Tolerate the usual shapes a retrieval function returns."""
    if isinstance(hit, str):
        return hit
    if isinstance(hit, dict):
        for key in ("chunk_id", "id"):
            if key in hit:
                return str(hit[key])
        payload = hit.get("payload") or {}
        if "chunk_id" in payload:
            return str(payload["chunk_id"])
    if isinstance(hit, (tuple, list)) and hit:
        return str(hit[0])
    for attr in ("chunk_id", "id"):
        if hasattr(hit, attr):
            return str(getattr(hit, attr))
    raise ValueError(f"Cannot extract chunk_id from hit: {hit!r}")

# ---------------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------------

CHUNKS = load_chunks()
CASES = [json.loads(l) for l in CASES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
POOLS = json.loads(POOLS_PATH.read_text(encoding="utf-8")) if POOLS_PATH.exists() else {}
DISPLAY_ORDER = {}   # case_id -> [chunk_id, ...] as shown on screen


def save_cases():
    with open(CASES_PATH, "w", encoding="utf-8") as f:
        for case in CASES:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")


def save_pools():
    POOLS_PATH.write_text(json.dumps(POOLS, ensure_ascii=False, indent=2), encoding="utf-8")


def build_pool(case: dict) -> dict:
    """Union of top-K from both query configurations. Cached."""
    cid = case["case_id"]
    if cid in POOLS:
        return POOLS[cid]

    q_problem = case["problem_text"]
    q_both = case["problem_text"] + "\n" + case["student_attempt"]

    ranks_problem = retrieve_topk(q_problem)
    ranks_both = retrieve_topk(q_both)

    union = list(dict.fromkeys(ranks_problem + ranks_both))
    POOLS[cid] = {
        "union": union,
        "rank_problem": {c: ranks_problem.index(c) + 1 for c in ranks_problem},
        "rank_both": {c: ranks_both.index(c) + 1 for c in ranks_both},
    }
    save_pools()
    return POOLS[cid]

# ---------------------------------------------------------------------------
# UI CALLBACKS
# ---------------------------------------------------------------------------

def render_case(idx: int):
    case = CASES[idx]
    cid = case["case_id"]
    pool = build_pool(case)

    order = list(pool["union"])
    random.Random(cid).shuffle(order)   # stable shuffle: same order on every visit
    DISPLAY_ORDER[cid] = order

    header = (
        f"### {cid} — case {idx + 1} of {len(CASES)}\n\n"
        f"**Problem**\n\n{case['problem_text']}\n\n"
        f"**Student attempt**\n\n{case['student_attempt']}\n\n"
        f"**Gold tag** — `{case.get('gold_tag', '')}`"
    )

    body = "\n\n---\n\n".join(
        f"**[{i + 1}]**\n\n{CHUNKS.get(c, '*(chunk text not found)*')}"
        for i, c in enumerate(order)
    )

    choices = [str(i + 1) for i in range(len(order))]
    saved = case.get("gold_chunk_ids") or []
    preselected = [str(order.index(c) + 1) for c in saved if c in order]

    labelled = sum(1 for c in CASES if c.get("gold_chunk_ids") is not None)
    progress = f"{labelled} of {len(CASES)} cases labelled"

    return (
        header, body,
        gr.update(choices=choices, value=preselected),
        case.get("notes", ""),
        bool(case.get("pool_miss", False)),
        progress,
        "",           # clear the reveal panel
    )


def save_current(idx: int, picks, notes, pool_miss):
    case = CASES[idx]
    order = DISPLAY_ORDER[case["case_id"]]
    case["gold_chunk_ids"] = [order[int(p) - 1] for p in picks]
    case["notes"] = notes
    case["pool_miss"] = bool(pool_miss)
    save_cases()

    labelled = sum(1 for c in CASES if c.get("gold_chunk_ids") is not None)
    ids = ", ".join(case["gold_chunk_ids"]) or "none"
    return f"Saved {case['case_id']} — gold: {ids}  ({labelled} of {len(CASES)} labelled)"


def reveal(idx: int):
    case = CASES[idx]
    pool = POOLS[case["case_id"]]
    order = DISPLAY_ORDER[case["case_id"]]
    lines = ["| shown | chunk_id | rank (problem) | rank (problem+attempt) |", "|---|---|---|---|"]
    for i, c in enumerate(order):
        rp = pool["rank_problem"].get(c, "—")
        rb = pool["rank_both"].get(c, "—")
        lines.append(f"| {i + 1} | `{c}` | {rp} | {rb} |")
    return "\n".join(lines)


def step(idx: int, delta: int):
    return max(0, min(len(CASES) - 1, idx + delta))

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

with gr.Blocks(title="Gold chunk labelling") as demo:
    gr.Markdown("## Gold chunk labelling")
    gr.Markdown(f"**Rule (frozen in SPEC.md):** {LABELLING_RULE}")

    idx_state = gr.State(0)

    with gr.Row():
        prev_btn = gr.Button("Previous case")
        next_btn = gr.Button("Next case")
        progress_box = gr.Markdown()

    header_md = gr.Markdown()

    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("### Pooled chunks — ranks and IDs hidden")
            body_md = gr.Markdown()
        with gr.Column(scale=1):
            picks = gr.CheckboxGroup(label="Gold chunks", choices=[])
            pool_miss = gr.Checkbox(
                label="Correct chunk is not in this pool",
                info="Tick when you know the right chunk exists in the corpus but retrieval never surfaced it.",
            )
            notes = gr.Textbox(
                label="Notes",
                info="Record cases where the rule felt wrong. These become the limitations section.",
                lines=4,
            )
            save_btn = gr.Button("Save labels", variant="primary")
            status = gr.Markdown()
            reveal_btn = gr.Button("Show ranks and IDs")

    reveal_md = gr.Markdown()

    outputs = [header_md, body_md, picks, notes, pool_miss, progress_box, reveal_md]

    demo.load(render_case, inputs=idx_state, outputs=outputs)

    prev_btn.click(lambda i: step(i, -1), idx_state, idx_state).then(
        render_case, idx_state, outputs)
    next_btn.click(lambda i: step(i, +1), idx_state, idx_state).then(
        render_case, idx_state, outputs)

    save_btn.click(save_current, [idx_state, picks, notes, pool_miss], status)
    reveal_btn.click(reveal, idx_state, reveal_md)

if __name__ == "__main__":
    demo.launch()
