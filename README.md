# Misconception Diagnosis for Greek Physics Exams — RAG Pipeline

Given a Panhellenic (Πανελλήνιες) collisions problem and a student's incorrect attempt, this system retrieves the relevant official methodology and surfaces **candidate misconceptions** from a hand-built taxonomy — for a tutor to confirm, not to replace one.

**Live demo:** [PLACEHOLDER — Hugging Face Spaces URL]

---

## Why this exists when frontier models already solve these problems

Frontier LLMs answer Panhellenic physics problems correctly out of the box. That was never the hard part. What they don't do:

Diagnose a *student's wrong attempt* against a tutor-validated misconception framework, grounded in the official exam methodology, with provenance the tutor can audit. A correct solution tells a student what the answer is. A grounded diagnosis tells a tutor *why this student got it wrong*, in the tutor's own vocabulary, with the official worked solution the attempt diverged from displayed alongside.

The system's value is grounded diagnosis with auditable provenance — not problem-solving.

**Proof the retrieval matters:** the demo includes an ablation toggle — the same query with retrieval on and off. Without retrieval, the model produces a generic textbook explanation: no exam-specific methodology, no taxonomy tag. With retrieval, the answer cites the specific past-exam solution and names a misconception ID that exists nowhere in any model's training data.

## The hard input problem: Greek + LaTeX OCR

The corpus is Greek-language physics exam material dense with mathematical notation. Off-the-shelf OCR fails on this combination: Greek text and Greek-letter math symbols (ω, φ, λ as *variables*, not language) collide constantly.

The ingestion pipeline uses Surya in math mode, converts `<math>` output to inline LaTeX delimiters, and emits page-separated Markdown. Getting clean, chunkable text out of these PDFs was the largest share of corpus preparation work, and everything downstream depends on it.

[PLACEHOLDER — before/after image: scanned exam page → extracted Markdown with LaTeX]

## Architecture

```
PDF exam papers (Greek)
   │  Surya OCR (math_mode) → Markdown + inline LaTeX
   ▼
Chunking (problem / solution-step / theory granularity)
   │  BGE-M3 embeddings (multilingual, strong on Greek)
   ▼
Qdrant vector store
   │  query = problem + student attempt
   ▼
Retrieval: relevant worked solutions + theory chunks
   │
   ▼
Generation (hosted frontier API), instructed to:
   1. ground the explanation in retrieved chunks (cited by ID)
   2. map the student's error to candidate tags from the
      misconception taxonomy (suggestion only — tutor confirms)
   ▼
UI (Gradio): input → retrieved context → diagnosis → candidate misconception
            (with a retrieval on/off ablation toggle)
```

## The misconception taxonomy

A hand-built list of collision misconceptions observed in real student work — e.g. treating kinetic energy as conserved in all collisions, applying momentum conservation only when an external force is present, conflating perfectly inelastic with "objects stop."

Each entry carries a `source` provenance field marking whether it was *observed* in direct tutoring or *constructed* from the literature — so the basis of every tag is auditable.

[PLACEHOLDER — excerpt of 3–4 taxonomy entries with IDs]

Design rule: **the LLM is never the authority on tags.** It suggests candidates from the fixed taxonomy; a human tutor confirms. This keeps the diagnostic layer auditable and the taxonomy improvable independently of the model.

## Corpus

Public Panhellenic collisions problems with official worked solutions, plus the collisions theory section from the openly published national physics textbook. Public material only, by design.

## Design decisions

**Frontier model over a small one.** A small model would showcase retrieval more dramatically — it can't solve exam physics from parametric knowledge alone. But retrieval supplies *knowledge*, not *reasoning*: reading a wrong attempt, locating where it diverges from the retrieved solution, and matching that divergence to a taxonomy entry is diagnostic reasoning small models fail at — and Greek input degrades them further. The retrieval ablation toggle demonstrates grounding without sacrificing diagnosis quality.

**Non-agentic pipeline.** A single retrieve → generate → tag pass is legible, debuggable, and fast to ship. Agentic orchestration adds failure modes without adding diagnostic value at this scale.

**[PLACEHOLDER — chunking granularity decision, once made]**

## Worked example

[PLACEHOLDER — one full example: problem, wrong attempt, retrieved chunks, generated diagnosis, confirmed misconception tag]

## Evaluation

A fixed eval set lives in the repo: collisions problems paired with wrong attempts and the misconception tag each should surface, built from the current taxonomy entries. Two numbers are reported:

- **Retrieval hit-rate** — fraction of cases whose correct source chunk appears in top-k. This is the floor: the diagnosis can only be as grounded as the retrieval beneath it.
- **Tag-suggestion accuracy** — fraction of cases where the confirmed misconception tag appears among the suggested candidates.

[PLACEHOLDER — report both numbers once the eval set is run]

## Running locally

```bash
git clone [PLACEHOLDER — repo URL]
cd [repo]
pip install -r requirements.txt
# [PLACEHOLDER — env vars: API key, Qdrant URL]
python app.py
```

## Status

Work in progress. OCR ingestion pipeline complete and validated on the collisions corpus; retrieval → generation → tagging loop in progress; not yet deployed. [Update as you go.]

## Scope

This is a deliberately narrow slice — one chapter (collisions), one exam family, one diagnostic loop — built end to end and deployed. It is not a tutoring platform.
