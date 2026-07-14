# SPEC — Collisions Misconception-Diagnosis RAG Demo

**One line:** A demo that takes a Panhellenic collisions problem and a
student's incorrect attempt, and returns a diagnosis grounded in retrieved
course methodology, with candidate misconception tags from a closed,
tutor-audited taxonomy for a tutor to confirm.

This document defines the scope and the definition of done. New ideas are
recorded in the Parking Lot rather than added to scope. Scope changes are
recorded in the Amendments section, dated — the contract is edited in the
open, never silently.

---

## Goal

A user opens the demo, supplies a collisions (κρούσεις) problem and a student's
wrong attempt in Greek, and receives:

- a diagnosis grounded in retrieved chunks of the collisions corpus, citing the
  chunks by ID;
- one or more candidate misconception tags from the fixed taxonomy (suggestions
  — a human tutor confirms);
- the retrieved source chunks shown alongside.

A vertical slice: one chapter, one diagnostic loop, end to end.

---

## Architecture

```
OCR'd markdown corpus (Greek + LaTeX)         misconception taxonomy (JSON, closed list)
   -> chunking (never split a $$...$$ block)              |
   -> embedding (BGE-M3, dense)                           |
   -> vector store (Qdrant, embedded mode)                |
        |                                                 |
   query = problem statement ONLY                         |
   -> retrieval (top-k worked-solution / theory chunks)   |
   -> prompt assembly (chunks, taxonomy, problem, attempt, instructions —
        instructions last, chunks first: positional-attention ordering)
   -> generation (hosted frontier LLM via API; provider isolated to one
        function):
        1. ground the explanation in retrieved chunks (cited by ID)
        2. locate where the attempt diverges from the retrieved solution
        3. suggest candidate tag(s) from the taxonomy (tutor confirms);
        output is a JSON contract validated in code — tags outside the
        closed list are rejected deterministically
   -> web UI (problem + attempt in; diagnosis + candidate tags + sources out;
              retrieval on/off ablation toggle; retrieved-chunks audit panel)
```

Each stage is one module. A stage is complete only after its output has been
inspected on real collisions data.

---

## Fixed decisions

- **Corpus:** the collisions chapter (ΚΕΦΑΛΑΙΟ 5: ΚΡΟΥΣΕΙΣ) — 62 exercises with
  worked solutions, chunked one exercise + solution per record. Public material
  only.
- **Source format:** page-separated markdown from a Surya OCR stack, LaTeX
  delimiters (`$...$` inline, `$$...$$` display).
- **Retrieval query = problem statement only** (resolved 2026-07-11; was an
  open decision). The corpus is correct physics; embedding the erroneous
  attempt risks pulling retrieval toward whatever correct topic the error
  imitates. The attempt enters the LLM prompt verbatim, never the query.
  Rejected: attempt-only, concatenation, dual-search-with-merge (parked).
- **Taxonomy:** a closed JSON label list — 15 tags in 4 categories plus a
  `NO_TAG_MATCH` escape hatch (resolved 2026-07-12). Provenance: AI-drafted
  from the corpus, tutor-audited; one tag (`ERR_SYS_ELASTIC_EXCHANGE`)
  challenged in audit and deliberately redefined as a method-efficiency error
  — the taxonomy covers best-practice errors, not only correctness errors.
  The LLM never authors tags; it suggests from the fixed set, a human
  confirms, and the parser rejects out-of-list tags in code. (The per-entry
  `source: observed|constructed` field from the original spec is deferred to
  the full taxonomy audit — see Parking Lot.)
- **Embeddings:** BGE-M3 (multilingual; handles Greek and math tokens),
  loaded via FlagEmbedding (native loader; keeps M3's sparse output available
  so hybrid retrieval is a config change, not a migration — corpus is dense
  with exact Greek physics tokens where sparse helps).
- **Vector store:** Qdrant, embedded mode (`./qdrant_data`) — what actually
  runs in a single-process deployment; payload carries chunk_id + text,
  frozen at index time.
- **Generation:** a hosted frontier LLM via API, with the provider isolated
  to a single function (proven swappable in one session: Anthropic → Gemini).
  Chosen over a small model deliberately — retrieval supplies knowledge, not
  the diagnostic reasoning of matching a divergence to a taxonomy entry, and
  Greek degrades small models further.
- **Pipeline shape:** a single retrieve -> generate -> tag pass. Non-agentic.
- **Proof of grounding:** an in-demo retrieval on/off ablation toggle.
  Empirical characterization (2026-07-12): on textbook-clear errors the tag
  matches with retrieval off — the demonstrated contribution of retrieval is
  auditability (checkable citations), not correctness on easy cases. The demo
  narrative states this honestly.

---

## Definition of done

1. **Demonstrable.** The demo runs end to end on the laptop, from a cold
   start, presentable at the Greeks in AI symposium (July 15–17). Cached
   outputs for the demo cases exist as the network-failure fallback.
   *(Amended 2026-07-12 — was: deployed to a public URL. See Amendments.)*
2. **Diagnostic loop.** Input is a problem + a student's wrong attempt. Output
   is a diagnosis grounded in retrieved chunks (cited by ID) plus one or more
   candidate misconception tags from the fixed taxonomy, presented as
   suggestions.
3. **Sources shown.** The retrieved chunks the diagnosis rests on are displayed
   alongside it.
4. **Ablation visible.** A toggle runs the same query with retrieval on and
   off, so the grounding contribution is demonstrable.
5. **Greek end to end.** Input to output, in Greek.
6. **Verified.** Demo cases spanning at least three taxonomy categories, each
   run in both retrieval modes, with any specific citation claims audited by
   hand against the corpus. *(Amended 2026-07-12 — the fixed eval set with
   reported hit-rate and tag-accuracy numbers moves to the first post-symposium
   milestone. See Amendments.)*
7. **Documented.** Code, spec, taxonomy, README — with run instructions and
   honest provenance statements (taxonomy origin; code-provided authorship).

---

## Out of scope

- Chapters other than collisions.
- Taxonomy expansion beyond the entries needed for the loop (see Parking Lot).
- Tutor workbench, the broader platform, multi-loop orchestration.
- Local LLM inference / GPU serving.
- User accounts, persistence, multi-user state.
- Reranking, query rewriting, agentic retrieval, fine-tuning.
- Hugging Face Spaces deployment (amended out 2026-07-12; first
  post-symposium milestone alongside the eval set).
- Polished or themed UI. The UI must show the problem+attempt input, the
  diagnosis, the candidate tags, the retrieved sources, and the ablation
  toggle — nothing beyond that.

---

## Components

- **Cleaning:** OCR markdown -> boilerplate-stripped markdown, removal audited.
- **Chunking:** markdown -> 62 JSONL records, one exercise + solution each;
  never splitting inside a `$$...$$` block.
- **Embedding:** BGE-M3 dense vectors over chunks, persisted with an explicit
  ID sidecar (pairing recorded at write time).
- **Store:** embedded Qdrant collection; payload = {chunk_id, text}.
- **Retrieval:** problem statement -> top-k chunks {chunk_id, text, score}.
- **Generation:** (problem, attempt, chunks, taxonomy) -> grounded diagnosis +
  1–3 candidate tags via hosted frontier LLM; JSON output validated against
  the closed list in code.
- **Taxonomy:** closed JSON list, tutor-audited; loaded as a generation input,
  never model-authored.
- **Ablation:** retrieval on/off path behind a UI toggle (one flag, not a
  second code path).
- **UI:** minimal Gradio interface over the diagnostic path, plus a collapsed
  audit panel showing retrieved chunks verbatim.

---

## Amendments

- **2026-07-11 — query construction resolved.** Problem-only retrieval,
  adopted from the open decision in the original architecture. Rationale
  recorded under Fixed decisions; rejected alternatives parked.
- **2026-07-12 — taxonomy format and provenance.** YAML -> JSON; "hand-built
  with per-entry source field" -> "AI-drafted, tutor-audited closed list with
  NO_TAG_MATCH"; the source-provenance field deferred to the full audit pass.
- **2026-07-12 — DoD items 1 and 6 re-scoped for the symposium deadline.**
  Deployment (public URL) and the fixed eval set with reported numbers move
  out of the slice, into the first post-symposium milestone. The slice's
  definition of done is: demonstrable on the laptop, verified on hand-audited
  cases across three taxonomy categories. Rationale: cut, don't extend — the
  July 14 deadline outranks both, and neither changes the diagnostic loop
  being demonstrated.

---

## Parking Lot

Ideas for later (not current commitments):

- **Post-symposium milestone 1 (promoted from DoD):** fixed eval set —
  (problem, wrong attempt, expected tag) cases; retrieval hit-rate and
  tag-suggestion accuracy reported in the README. Hugging Face Spaces
  deployment.
- Full per-tag taxonomy audit; tags added from own graded-paper experience;
  per-entry `source: observed|constructed` provenance field.
- Hybrid dense+sparse retrieval (lexical_weights available from BGE-M3;
  needs collection rebuild + fusion choice; two empirical motivations:
  one-word-swap experiment, opposite-direction configuration miss).
- Citation tightening: instruct citing only chunks the justification relies on.
- Reranking / query rewriting; attempt-only or dual-search retrieval variants.
- Chapters beyond collisions.
- Tutor confirmation workflow / persistence.
- Model the student as a state object (misconception-state over time),
  complex-systems lens: stable vs. transient misconceptions, transitions under
  intervention.
- Methodology layer: hand-authored methodology per exercise case, with
  methodology tags alongside misconception tags, enabling tutor-on-demand
  exercise retrieval by tag.
