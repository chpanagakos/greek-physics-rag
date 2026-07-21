---
title: Greek Physics RAG
emoji: 🔬
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 6.20.0
app_file: app.py
pinned: false
license: other
---

# Auditable Misconception Diagnosis for Greek Physics Exams

A retrieval-augmented generation (RAG) pipeline for tutor review.

Given a Panhellenic (Πανελλαδικές) collisions problem and a student's incorrect attempt, this system retrieves the relevant course methodology and surfaces **candidate misconceptions** from a closed, tutor-audited taxonomy — for a tutor to confirm, not to replace one.

**Live demo:** https://huggingface.co/spaces/chpanagakos/greek-physics-rag

Deployed on Hugging Face Spaces (CPU, free tier). This is a public demonstrator, not a production service: no SLOs, monitoring, or operational infrastructure. The Gemini free-tier quota is shared across all visitors, so the demo may occasionally report that the API limit is temporarily exhausted.

Ten worked cases are available as click-to-fill examples; each runs the live pipeline rather than replaying a cached result.

*Privacy:* Inputs are sent to the configured Gemini API for generation. Do not enter student names, contact details or other sensitive information into the public demo.

---

## Why this exists when frontier models already solve these problems
Frontier LLMs can often solve standard Greek national university-entrance examinations (Panhellenic exams) physics problems without retrieval. What they don't do:

Diagnose a *student's wrong attempt* against a tutor-audited misconception framework, grounded in course material, with provenance the tutor can audit. A correct solution tells a student what the answer is. A grounded diagnosis tells a tutor *why this student got it wrong*, in the tutor's own vocabulary, with the worked material that the attempt diverged from, which is displayed alongside.

The system's value is grounded diagnosis with auditable provenance — not problem-solving.

**Proof the retrieval matters:** the demo includes an ablation toggle — the same query with retrieval on and off. The honest finding, observed empirically: on textbook-clear errors, a frontier model names the misconception correctly *even without retrieval*. What retrieval changes is not correctness but **checkability**. With retrieval on, the diagnosis cites specific corpus chunks by ID — claims a tutor can verify against the source in seconds. With retrieval off, the same diagnosis is "trust me." For a tool whose output feeds grading decisions, checkable beats confident.

## The hard input problem: Greek + LaTeX OCR

The corpus is Greek-language physics exam material dense with mathematical notation. The general-purpose OCR systems tested during development performed poorly on this combination: Greek text and Greek-letter math symbols (ω, φ, λ as *variables*, not language) collide constantly.

The ingestion pipeline uses Surya in math mode, converts `<math>` output to inline LaTeX delimiters, and emits page-separated Markdown. Getting clean, chunkable text out of these PDFs was the largest share of corpus preparation work, and everything downstream depends on it.

## Architecture

```
PDF exam material (Greek)
   │  Surya OCR (math_mode) → Markdown + inline LaTeX
   │  cleaning (boilerplate stripped, audited: zero content casualties, graphs aside)
   ▼
Chunking — one exercise + worked solution per chunk (62 chunks)
   │  BGE-M3 dense embeddings (multilingual, selected for satisfactory Greek retrieval behaviour in project testing)
   ▼
Qdrant vector store (embedded mode; payload carries chunk_id + text,
   │                  frozen at index time — provenance by construction)
   │  query = problem statement ONLY (see Design decisions)
   ▼
Retrieval: top-k relevant worked solutions + theory
   │
   ▼
Generation (frontier LLM; provider isolated to one function), instructed to:
   1. ground the diagnosis in retrieved chunks (cited by ID)
   2. map the student's error to 1–3 candidate tags from the
      closed misconception taxonomy (suggestion only — tutor confirms)
   Output is a JSON contract, validated in code: tags outside the
   closed list are rejected deterministically.
   ▼
UI (Gradio): input → diagnosis → candidate tags → cited chunk IDs
             → audit panel showing retrieved chunks verbatim
             (with a retrieval on/off ablation toggle)
```

## The misconception taxonomy

A closed label list for collision misconceptions: 15 tags in four categories (vector/directional errors, conservation-law misapplications, system/state misidentification, algebraic execution), plus an explicit `NO_TAG_MATCH` escape hatch so the model is never forced into a bad fit.

**Provenance, stated plainly:** the taxonomy was AI-drafted from the corpus, then audited by me. The audit was not a rubber stamp — one tag (`ERR_SYS_ELASTIC_EXCHANGE`) was challenged and deliberately redefined as a *method-efficiency* error: it flags a student who reaches the correct answer for an equal-mass elastic collision through full algebra instead of the velocity-exchange property. The taxonomy encodes what a tutor grades, not only what physics forbids — a correct final answer can still earn a tag. A full per-tag audit pass and tags drawn from my own graded papers are on the roadmap.

Example entries:

- `ERR_CONSV_KE_PLASTIC` — student sets K_initial = K_final for a completely inelastic collision
- `ERR_VEC_SUB_SIGN` — sign convention dropped when velocities oppose; Δv computed as v − v instead of v − (−v)
- `ERR_MATH_PCT_BASE` — percentage energy loss computed against the final energy instead of the initial
- `ERR_SYS_ELASTIC_EXCHANGE` — correct result, missed best practice (see above)

Design rule: **the LLM is never the authority on tags.** It suggests candidates from the fixed taxonomy; a human tutor confirms. The parser enforces this in code — a hallucinated tag raises an error rather than reaching the tutor. This keeps the diagnostic layer auditable and the taxonomy improvable independently of the model.

## Licence and corpus

**Code** (`*.py`, configuration, `taxonomy.json`): MIT.

**Corpus** (`chunks.jsonl` and the text payloads in the shipped Qdrant collection): derived from Greek upper-secondary physics material published by ΙΤΥΕ «Διόφαντος», licensed CC BY-NC-SA. These files are redistributed here under the same licence, with attribution to ΙΤΥΕ «Διόφαντος» as the original distributor. They are OCR-extracted and chunked, not modified in substance.

The MIT licence does not extend to the corpus material.
## Design decisions

**Frontier model over a small one.** A small model would showcase retrieval more dramatically — it can't solve exam physics from parametric knowledge alone. But retrieval supplies *knowledge*, not *reasoning*: reading a wrong attempt, locating where it diverges from the retrieved solution, and matching that divergence to a taxonomy entry is diagnostic reasoning that smaller models handled less reliably in project testing — and Greek input degrades them further. The retrieval ablation toggle demonstrates grounding without sacrificing diagnosis quality.

**Query = problem statement only.** The student's attempt enters the LLM prompt verbatim but never the retrieval query. The corpus is correct physics; embedding erroneous physics risks pulling retrieval toward whatever correct topic the error superficially imitates. Rejected alternatives (attempt-only, concatenation, dual-search-with-merge) are documented in the repo history.

**Prompt block ordering.** Retrieved chunks first, task instructions last, taxonomy and problem/attempt in the middle — following the "lost in the middle" positional-attention findings (Liu et al.): the two blocks whose neglect is catastrophic (grounding material; the instruction to cite it) occupy the two attention-anchored positions.

**One exercise + solution per chunk.** Exercises are the corpus's natural retrieval unit: a hit arrives as a complete worked example the diagnosis can cite as a whole, and chunk IDs (`erotisi-35`) map one-to-one to sources a tutor recognizes. Finer granularity (solution-step chunks) is a measured trade-off deferred until retrieval metrics justify it.

**Non-agentic pipeline.** A single retrieve → generate → tag pass is legible, debuggable, and fast to ship. Agentic orchestration adds failure modes without adding diagnostic value at this scale.

## Worked example

Problem: sphere A (mass m, speed v) collides head-on and perfectly inelastically with resting sphere B (mass 2m); find the post-collision speed.

Student attempt: applies conservation of *kinetic energy* through the collision, deriving V = v/√3.

System output (retrieval on): candidate tag `ERR_CONSV_KE_PLASTIC`; justification in Greek stating the student conserved kinetic energy through a plastic collision where energy is necessarily lost; citations `erotisi-35`, `erotisi-36` — two corpus problems that explicitly state a 25% kinetic-energy loss in plastic collisions. The cited claim was verified against the corpus text directly.

Same input, retrieval off (ablation): same tag, no citations — a correct diagnosis with nothing for the tutor to check.

## Evaluation

Current state: smoke-tested end to end on 10 cases, with citation claims manually audited against the corpus. A fixed eval set with two reported numbers is the next milestone:

- **Retrieval hit-rate** — fraction of cases whose correct source chunk appears in top-k. This is the floor: the diagnosis can only be as grounded as the retrieval beneath it.
- **Tag-suggestion accuracy** — fraction of cases where the confirmed misconception tag appears among the suggested candidates.

One retrieval limitation is already characterized empirically: dense-only retrieval discriminates *topic* well but *collision-type* weakly (a one-word πλαστικά→ελαστικά swap barely reorders results). The named fix — hybrid dense+sparse using BGE-M3's lexical weights — is on the roadmap.

## Limitations

- **Corpus:** one chapter (ΚΕΦΑΛΑΙΟ 5, collisions), 62 chunks. Greek upper-secondary Panhellenic material only. Nothing outside collisions is retrievable, and the system will still attempt a diagnosis rather than declining — out-of-scope input is not currently detected.
- **Retrieval:** dense only. Collision-type discrimination is empirically weak (see Evaluation); the hybrid dense+sparse fix is named but not built.
- **Evaluation:** no formal benchmark yet. Claims are supported by end-to-end smoke tests and manual citation audits, not measured accuracy.
- **Figures and graphs:** the corpus is text and LaTeX. Questions whose content depends on a diagram, or whose expected answer is a sketched graph, are outside what the system can ground a diagnosis in.
- **Unit of diagnosis:** one problem and one attempt per submission. Multi-part exam questions (Γ1–Γ4) must be submitted separately; pasted as a block, the output schema degrades silently.
- **Quota:** the deployed demo runs on the Gemini free tier, shared across all visitors and exhaustible.
- **Not autonomous:** output is 1–3 *candidate* tags for a tutor to confirm. The system is a diagnostic aid, not a grader.

## Authorship

The architecture, every design decision above, and the taxonomy audit are mine. Implementation code was written in collaboration with LLM assistants (Claude), with ownership at the decision and explanation level. The OCR pipeline follows the same disclosure (documented in its module).

## Running locally

```bash
git clone https://github.com/chpanagakos/greek-physics-rag
cd greek-physics-rag
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=...   # provider is isolated to one function; swappable
python app.py               # Gradio UI at localhost:7860

# The Qdrant collection ships with the repo (62 chunks, embedded mode).
# To rebuild it from source instead:
python embed.py        # chunks.jsonl → embeddings.npy (GPU optional)
python load_qdrant.py  # embeddings.npy → local Qdrant collection
```
## Status
Vertical slice complete and deployed: OCR ingestion → cleaning → chunking → embeddings → Qdrant → retrieval → grounded diagnosis → Gradio UI with ablation toggle, running publicly on Hugging Face Spaces. The evaluation set is the next milestone.

## Scope

This is a deliberately narrow slice — one chapter (collisions), one exam family, one diagnostic loop — built end to end. It is not a tutoring platform.

## References and components

**Prompt block ordering** — Liu, N.F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., Liang, P. (2024). *Lost in the Middle: How Language Models Use Long Contexts.* Transactions of the ACL, 12:157–173. [arXiv:2307.03172](https://arxiv.org/abs/2307.03172) · [ACL Anthology](https://aclanthology.org/2024.tacl-1.9/)

**Embeddings** — BGE-M3 ([BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3)). Chen, J., Xiao, S., Zhang, P., Luo, K., Lian, D., Liu, Z. (2024). *M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation.* Findings of the ACL 2024, 2318–2335. [arXiv:2402.03216](https://arxiv.org/abs/2402.03216)

**OCR** — [Surya](https://github.com/datalab-to/surya) (datalab-to), used in math mode for Greek text with inline mathematical notation.

**Vector store** — [Qdrant](https://github.com/qdrant/qdrant), Apache-2.0, run in embedded mode.

**UI** — [Gradio](https://github.com/gradio-app/gradio).

**Generation** — [Gemini API](https://ai.google.dev/) (gemini-2.5-flash). The provider is isolated to a single function; see Design decisions.

**Corpus** — [study4exams.gr — ΚΕΦΑΛΑΙΟ 5: ΚΡΟΥΣΕΙΣ (PDF)](https://www.study4exams.gr/physics_k/pdf/FK_K5_E/FK_K5_E_A.pdf), ΙΤΥΕ «Διόφαντος». See Licence and corpus.
