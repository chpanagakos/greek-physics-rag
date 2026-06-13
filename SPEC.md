# SPEC — Collisions Misconception-Diagnosis RAG Demo

**One line:** A deployed demo that takes a Panhellenic collisions problem and a
student's incorrect attempt, and returns a diagnosis grounded in retrieved
official methodology, with candidate misconception tags from a hand-built
taxonomy for a tutor to confirm.

This document defines the scope and the definition of done. New ideas are
recorded in the Parking Lot rather than added to scope.

---

## Goal

A user opens the demo, supplies a collisions (κρούσεις) problem and a student's
wrong attempt in Greek, and receives:

- a diagnosis grounded in retrieved chunks of the collisions corpus, citing the
  chunks by ID;
- one or more candidate misconception tags from the fixed taxonomy (suggestions
  — a human tutor confirms);
- the retrieved source chunks shown alongside.

A vertical slice: one chapter, one diagnostic loop, end to end, deployed.

---

## Architecture

```
OCR'd markdown corpus (Greek + LaTeX)         misconception taxonomy (YAML, hand-built)
   -> chunking (never split a $$...$$ block)              |
   -> embedding (BGE-M3)                                  |
   -> vector store (Qdrant)                               |
        |                                                 |
   query = problem + student attempt                      |
   -> retrieval (top-k worked-solution / theory chunks)   |
   -> prompt assembly (problem + attempt + chunks + taxonomy)
   -> generation (hosted frontier LLM via API):
        1. ground the explanation in retrieved chunks (cited by ID)
        2. locate where the attempt diverges from the retrieved solution
        3. suggest candidate tag(s) from the taxonomy (tutor confirms)
   -> web UI (problem + attempt in; diagnosis + candidate tags + sources out;
              retrieval on/off ablation toggle)
```

Each stage is one module. A stage is complete only after its output has been
inspected on real collisions data.

Open design decision (resolve when wiring retrieval, not by default): the
retrieval query is currently `problem + student attempt`. The wrong attempt can
pull retrieval off the correct worked solution; it may also surface the relevant
theory chunk. Mitigations (reranking, query rewriting, problem-only retrieval)
are parked, not adopted, until hit-rate is measured.

---

## Fixed decisions

- **Corpus:** the collisions chapter — public Panhellenic problems with official
  worked solutions, plus the national textbook collisions theory section. Public
  material only.
- **Source format:** page-separated markdown from a Surya OCR stack, LaTeX
  delimiters (`$...$` inline, `$$...$$` display).
- **Taxonomy:** a hand-built YAML list of collision misconceptions, each with a
  `source` provenance field (`observed` vs `constructed`). The LLM never authors
  tags; it suggests from the fixed set, a human confirms.
- **Embeddings:** BGE-M3 (multilingual; handles Greek and math tokens).
- **Vector store:** Qdrant.
- **Generation:** a hosted frontier LLM via API. Chosen over a small model
  deliberately — retrieval supplies knowledge, not the diagnostic reasoning of
  matching a divergence to a taxonomy entry, and Greek degrades small models
  further.
- **Pipeline shape:** a single retrieve -> generate -> tag pass. Non-agentic.
- **Proof of grounding:** an in-demo retrieval on/off ablation toggle.

---

## Definition of done

1. **Deployed.** A public URL serves the demo, independent of any local machine.
2. **Diagnostic loop.** Input is a problem + a student's wrong attempt. Output is
   a diagnosis grounded in retrieved chunks (cited by ID) plus one or more
   candidate misconception tags from the fixed taxonomy, presented as
   suggestions.
3. **Sources shown.** The retrieved chunks the diagnosis rests on are displayed
   alongside it.
4. **Ablation visible.** A toggle runs the same query with retrieval on and off,
   so the grounding contribution is demonstrable.
5. **Greek end to end.** Input to output, in Greek.
6. **Evaluated.** A fixed eval set lives in the repo: (problem, wrong attempt,
   expected tag) cases built from the existing taxonomy entries. The README
   reports retrieval hit-rate (correct source chunk in top-k) and tag-suggestion
   accuracy (expected tag present among the suggested candidates) on that set.
7. **Documented.** Code, spec, taxonomy, eval set, README — with run
   instructions and the reported numbers.

---

## Out of scope

- Chapters other than collisions.
- Taxonomy expansion beyond the entries needed to build and evaluate the loop
  (see Parking Lot).
- Tutor workbench, the broader platform, multi-loop orchestration.
- Local LLM inference / GPU serving.
- User accounts, persistence, multi-user state.
- Reranking, query rewriting, agentic retrieval, fine-tuning.
- Polished or themed UI. The UI must show the problem+attempt input, the
  diagnosis, the candidate tags, the retrieved sources, and the ablation toggle
  — nothing beyond that.

---

## Components

- **Chunking:** markdown -> chunks, never splitting inside a `$$...$$` block.
- **Embedding:** BGE-M3 over chunks.
- **Store:** Qdrant collection of chunk vectors.
- **Retrieval:** (problem + attempt) -> top-k chunks.
- **Generation:** (problem + attempt + chunks + taxonomy) -> grounded diagnosis +
  candidate tags via hosted frontier LLM.
- **Taxonomy:** hand-built YAML, provenance-tagged; loaded as a generation input,
  never model-authored.
- **Ablation:** retrieval on/off path behind a UI toggle.
- **UI:** minimal web interface over the diagnostic path.
- **Evaluation:** fixed (problem, attempt, expected tag) set; retrieval hit-rate
  and tag-suggestion accuracy reported.

---

## Parking Lot

Ideas for later (not current commitments):

- Taxonomy expansion beyond the entries needed for the loop and the eval set.
- Reranking / query rewriting to handle the contaminated query (problem + wrong
  attempt pulling retrieval off-target), or problem-only retrieval.
- Chapters beyond collisions.
- Tutor confirmation workflow / persistence.
- Model the student as a state object (misconception-state over time),
  complex-systems lens: stable vs. transient misconceptions, transitions under
  intervention.
- Methodology layer: hand-authored methodology per exercise case, with
  methodology tags alongside misconception tags, enabling tutor-on-demand
  exercise retrieval by tag.
