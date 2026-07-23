# SPEC — Collisions Misconception-Diagnosis RAG Demo

**One line:** A demo that takes a Panhellenic collisions problem and a
student's incorrect attempt, and returns a diagnosis grounded in retrieved
course methodology, with candidate misconception tags from a closed,
tutor-audited taxonomy for a tutor to confirm.

This document defines the current scope and completion criteria. Proposed
extensions are recorded in the Parking Lot, while adopted scope changes are
documented by date in the Amendments section.

---

## Goal

A user opens the demo, supplies a collisions (κρούσεις) problem and a student's
incorrect attempt in Greek, and receives:

- a diagnosis grounded in retrieved chunks of the collisions corpus, citing the
  chunks by ID;
- one or more candidate misconception tags from the fixed taxonomy (suggestions
  — a human tutor confirms);
- the retrieved source chunks shown alongside.

The current scope covers one chapter and one end-to-end diagnostic workflow.

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
- **Retrieval query = problem statement only** (resolved 2026-07-11;
  rationale revised 2026-07-23 — see Amendments). The student's attempt is
  included verbatim in the generation prompt but not in the deployed
  retrieval query. On the development set, a combined problem-and-attempt
  query improved Recall@5 from 8/10 to 10/10. Because the evaluated attempts
  are uniformly articulate, AI-generated prose, the result may not extend to
  sparse algebra, ambiguous wording or incorrect terminology in real student
  work. The problem-only query is retained pending evaluation on a held-out
  set with varied response forms. Attempt-only retrieval remains out of scope;
  separate problem and attempt searches with rank fusion remain a Parking Lot
  candidate.
- **Taxonomy:** a closed JSON label list for momentum-and-collision
  misconceptions — 15 tags in 4 categories plus a `NO_TAG_MATCH` outcome
  (resolved 2026-07-12; scope wording widened 2026-07-23 to reflect the
  inclusion of explosions and momentum-conservation problems). The taxonomy
  was drafted with AI assistance from the corpus and subsequently reviewed by
  the author. The generation model proposes labels from the fixed set, a tutor
  makes the final determination, and the parser rejects labels outside the
  list. Per-entry `source: observed|constructed` metadata remains deferred to
  the full taxonomy review in the Parking Lot.
- **Embeddings:** BGE-M3, loaded through FlagEmbedding for multilingual dense
  embeddings. The model's sparse lexical weights remain available for future
  hybrid-retrieval evaluation; using them would require a collection rebuild
  and a defined rank-fusion strategy.
- **Vector store:** Qdrant in embedded mode (`./qdrant_data`), matching the
  single-process deployment. Each payload stores the immutable `chunk_id` and
  source text associated with the vector at index time.
- **Generation:** a hosted frontier LLM accessed through a provider interface
  isolated to one function; the implementation has been used with both
  Anthropic and Gemini. Preliminary project testing found smaller models less
  reliable when comparing Greek-language student attempts with retrieved
  solutions and assigning taxonomy labels.
- **Pipeline shape:** a single retrieve -> generate -> tag pass. Non-agentic.
- **Retrieval ablation:** the interface includes a retrieval on/off toggle.
  On the development set (2026-07-23), tag accuracy was 10/10 with retrieval
  and 9/10 without it. Retrieval did not change the correct diagnosis in nine
  cases, although it provided material for inspection; in one case it changed
  an incorrect diagnosis to the correct one. These are development-set
  observations rather than general performance estimates.
- **Evaluation protocol** (added 2026-07-23): a development / test split.
  The 10-case development set (`eval/cases.jsonl`) has known construction
  biases — shared authorship between taxonomy and cases, pooled gold-chunk
  labelling — and is used for harness verification and design experiments.
  Claims about system quality are reserved for a held-out test set,
  independently authored from observed student errors, with attempts
  varying in articulateness by design, against which prompts and taxonomy
  are never tuned.

---

## Definition of done

1. **Demonstrable.** The demo runs end to end on the laptop, from a cold
   start, presentable at the Greeks in AI symposium (July 15–17). Cached
   outputs for the demo cases exist as the network-failure fallback.
   *(Amended 2026-07-12 — was: deployed to a public URL. See Amendments.)*
2. **Diagnostic loop.** Input consists of a problem and a student's incorrect
   attempt. Output consists of a diagnosis associated with cited retrieved
   chunks and one or more candidate labels from the fixed taxonomy.
3. **Sources shown.** The retrieved chunks the diagnosis rests on are displayed
   alongside it.
4. **Ablation visible.** A toggle runs the same case with retrieval enabled
   or disabled so the two outputs can be compared directly.
5. **Greek end to end.** Input to output, in Greek.
6. **Verified.** Demo cases spanning at least three taxonomy categories, each
   run in both retrieval modes, with any specific citation claims audited by
   hand against the corpus. *(Amended 2026-07-12 — the fixed eval set with
   reported hit-rate and tag-accuracy numbers moves to the first post-symposium
   milestone. See Amendments.)*
7. **Documented.** Code, specification, taxonomy and README include local run
   instructions, taxonomy provenance and disclosure of AI-assisted development.

---

## Out of scope

- Chapters other than collisions.
- Taxonomy expansion beyond the entries needed for the loop (see Parking Lot).
- Tutor workbench, the broader platform, multi-loop orchestration.
- Local LLM inference / GPU serving.
- User accounts, persistence, multi-user state.
- Reranking, query rewriting, agentic retrieval, fine-tuning.
- Polished or themed UI. The required interface is limited to the
  problem-and-attempt input, diagnosis, candidate labels, retrieved sources
  and retrieval-ablation toggle.

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
- **Taxonomy:** closed, tutor-reviewed JSON list supplied to the generation
  model; output labels are validated against this list.
- **Ablation:** retrieval on/off path behind a UI toggle (one flag, not a
  second code path).
- **UI:** minimal Gradio interface over the diagnostic path, plus a collapsed
  audit panel showing retrieved chunks verbatim.
- **Evaluation harness** (added 2026-07-23): `eval/cases.jsonl` (cases with
  hand-assigned gold tags and hand-labelled gold chunks, with provenance
  fields), `eval/run_cases.py` (resumable prediction runner, both retrieval
  conditions), offline scorers for tag accuracy, Recall@k/MRR, query
  construction, and citation validity; `eval/label_tool.py` (internal
  gold-chunk labelling scaffold, blind to rank and chunk ID).

---

## Amendments

- **2026-07-11 — query construction resolved.** Problem-only retrieval,
  adopted from the open decision in the original architecture. Rationale
  recorded under Fixed decisions; rejected alternatives parked.
- **2026-07-12 — taxonomy format and provenance.** YAML -> JSON; "hand-built
  with per-entry source field" -> "AI-drafted, tutor-audited closed list with
  NO_TAG_MATCH"; the source-provenance field deferred to the full audit pass.
- **2026-07-12 — DoD items 1 and 6 re-scoped for the symposium deadline.**
  Public deployment and a fixed evaluation set with reported results were
  moved to the first post-symposium milestone. For the July 14 deadline, the
  completion criteria were limited to a laptop demonstration and manually
  reviewed cases spanning three taxonomy categories.
- **2026-07-21 — Hugging Face Spaces deployment completed.** Public
  deployment was completed and removed from Out of scope. The deployment is
  maintained as a public demonstrator rather than an operational service.
- **2026-07-23 — taxonomy scope wording widened.** "Collision misconceptions"
  -> "momentum-and-collision misconceptions", matching the corpus, which
  includes explosions and momentum-conservation questions (its first chunk
  is an explosion problem). Category descriptions to be aligned in the full
  audit pass; no tags added or removed by this amendment.
- **2026-07-23 — development evaluation set added; development/test split
  adopted.** The development set contains 10 cases with manually assigned
  labels and source-chunk relevance judgements. Reported measures include tag
  accuracy under both retrieval conditions, Recall@k, MRR, query construction
  and citation validity. Because the cases and taxonomy have related
  authorship and the relevance pool originated from retriever output, primary
  performance estimates are deferred to an independently constructed
  held-out set.
- **2026-07-23 — query-construction rationale revised; deployed decision
  retained.** The combined problem-and-attempt query achieved Recall@5 of
  10/10, compared with 8/10 for problem-only retrieval. The current
  development set does not test whether this improvement persists across
  sparse algebra, ambiguous wording or incorrect terminology. Problem-only
  retrieval therefore remains deployed until the held-out evaluation is
  available. Separate problem and attempt searches with rank fusion moved
  from rejected to Parking Lot candidate.

---

## Parking Lot

Ideas for later (not current commitments):

- **Held-out test set:** independently constructed cases derived from observed
  student errors, with two cases per applicable label and deliberate variation
  in response form, including bare algebra and incorrect terminology. Relevant
  chunks will be assigned through an exhaustive corpus audit rather than
  retrieval-result pooling. This set will be used to compare query strategies
  and estimate primary system performance.
- Deterministic test layer: pytest over the parser, taxonomy integrity, and
  eval-file invariants; citation-validity promoted from observed to enforced
  (assert cited IDs ⊆ retrieved set). Minimal GitHub Actions running it.
- Citation-support review: classify cited chunks as directly supporting,
  defensible alternatives or non-supporting across the evaluation set.
- Complete per-label taxonomy review informed by previously graded student
  solutions; add `source: observed|constructed` provenance metadata, align
  category descriptions with the widened scope, and define an explicit
  outcome for fully correct work.
- Evaluate hybrid dense and sparse retrieval using BGE-M3 lexical weights.
  This requires a collection rebuild and a defined fusion method. Motivation
  comes from the limited ranking change in the one-word substitution test and
  the configuration-level misses observed on the development set.
- Citation selection: evaluate whether prompt changes can improve support
  precision without reducing coverage of relevant material. Development-set
  output averaged 1.7 citations per case.
- Reranking and query rewriting; attempt-only retrieval; and separate problem
  and attempt searches with rank fusion. The last option retains the attempt's
  disambiguating terms while keeping the textbook problem as an independent
  retrieval signal. Selection between these approaches is deferred until the
  held-out test set is available.
- Chapters beyond collisions.
- Tutor confirmation workflow / persistence.
- Model the student as a state object (misconception-state over time),
  complex-systems lens: stable vs. transient misconceptions, transitions under
  intervention.
- Methodology layer: hand-authored methodology per exercise case, with
  methodology tags alongside misconception tags, enabling tutor-on-demand
  exercise retrieval by tag.
