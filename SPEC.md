# Engineering Specification — Greek Physics Diagnostic RAG

**Status:** Implemented public demonstrator  
**Current scope:** Momentum and collisions  
**Interface:** Gradio  
**Last updated:** 2026-07-24

This document defines the implemented system, its enforced contracts, the
evaluation protocol and the boundary of the current project. Operating
instructions and the shorter project overview belong in the README; proposed
extensions are listed here only where they affect future evaluation or
architecture.

---

## 1. Purpose

The system assists a physics tutor in reviewing an incorrect student solution
written in Greek. Given a problem statement and the student's attempt, it:

1. retrieves relevant theory or worked-solution passages from a fixed corpus;
2. produces a diagnosis that cites passages returned by retrieval;
3. proposes one to three labels from a closed misconception taxonomy; and
4. displays the retrieved passages and model output for tutor review.

The model output is advisory. The tutor determines whether the explanation is
well supported and whether the proposed labels accurately describe the
student's reasoning.

---

## 2. Scope

### Included

- Greek-language problems and student attempts.
- The momentum-and-collisions chapter of the source corpus.
- Dense retrieval over 62 exercise-and-solution chunks.
- A 15-label misconception taxonomy in four categories, plus
  `NO_TAG_MATCH`.
- A single retrieval-and-generation pass.
- Deterministic validation of output structure, labels and citation IDs.
- A retrieval on/off ablation.
- A Gradio interface, local execution, container execution and public
  deployment.
- An offline evaluation harness with manually assigned misconception and
  source-relevance labels.

### Excluded from the current system

- Other physics chapters.
- Automated grading or an authoritative diagnosis.
- User accounts, longitudinal student records or multi-user persistence.
- Agentic retrieval, query rewriting, reranking or fine-tuning.
- Local model serving.
- Containerised OCR ingestion.
- A full tutor workbench or production service-level guarantees.

---

## 3. System contract

### 3.1 Inputs

The diagnostic path accepts:

- a Greek physics problem statement;
- a Greek student attempt; and
- a retrieval mode: enabled or disabled.

When retrieval is enabled, the deployed search query contains the problem
statement only. The student attempt is passed to the generation model but is
not included in the search query.

### 3.2 Outputs

The system returns:

- a diagnostic explanation in Greek;
- one to three candidate misconception labels;
- cited corpus chunk IDs;
- the retrieved passages and their similarity scores; and
- the active retrieval mode.

### 3.3 Enforced invariants

Before an output reaches the interface, the application verifies that:

- the response conforms to the expected JSON structure;
- every proposed label belongs to the closed taxonomy; and
- every cited chunk ID belongs to the set returned by retrieval.

An invalid response is rejected rather than silently repaired. The citation
subset rule is implemented by `validate_citations()`.

### 3.4 Human-review boundary

| Property | Enforced by code | Reviewed by a tutor |
|---|:---:|:---:|
| Valid JSON structure | Yes | No |
| Labels belong to the taxonomy | Yes | No |
| Cited IDs were retrieved | Yes | No |
| A citation supports the associated claim | No | Yes |
| A proposed label fits the student's reasoning | No | Yes |
| The diagnosis is pedagogically useful | No | Yes |

This distinction is part of the system contract: citation validity means that
a cited identifier is traceable to retrieved material, not that textual
support has been established automatically.

---

## 4. Architecture

```text
Source PDF
  → Surya OCR and cleaning
  → structure-aware chunking
  → BGE-M3 dense embeddings
  → embedded Qdrant collection

Problem statement
  → top-k retrieval ───────────────┐
Student attempt ───────────────────┤
Closed taxonomy ───────────────────┤
                                   ↓
                           prompt assembly
                                   ↓
                         hosted generation model
                                   ↓
                  schema, label and citation validation
                                   ↓
                      diagnosis, labels and sources
```

The runtime is deliberately non-agentic. It performs one retrieval step
followed by one generation step and one deterministic validation step.

### 4.1 Component responsibilities

| Component | Input | Output | Responsibility |
|---|---|---|---|
| OCR and cleaning | Source PDF | Page-separated Markdown | Recover Greek text and mathematical notation; remove repeated boilerplate |
| Chunking | Clean Markdown | `data/chunks.jsonl` | Preserve one exercise with its solution and avoid splitting display-math blocks |
| Embedding | Corpus chunks | Dense vectors and ID mapping | Encode Greek scientific text with BGE-M3 |
| Vector store | Vectors and payloads | Embedded Qdrant collection | Persist each vector with its immutable `chunk_id` and text |
| Retrieval | Problem statement | Top-k chunks with scores | Select candidate context for generation and audit |
| Prompt assembly | Problem, attempt, chunks, taxonomy | Model request | Separate source material from user content and place instructions last |
| Generation | Model request | Structured diagnosis | Produce an explanation, candidate labels and citations |
| Validation | Structured diagnosis and retrieved IDs | Accepted output or error | Enforce the deterministic output contract |
| Interface | User input and accepted output | Gradio view | Expose the diagnostic path, ablation control and source audit panel |

The hosted-model provider is isolated behind one interface so that provider
changes do not alter retrieval, validation or evaluation logic.

---

## 5. Corpus and ingestion

### 5.1 Source

The current corpus is built from the public momentum-and-collisions chapter:

- File: `FK_K5_E_A.pdf`
- Source:
  [Study4Exams PDF](https://www.study4exams.gr/physics_k/pdf/FK_K5_E/FK_K5_E_A.pdf)
- Result: 62 records, each containing one exercise and its worked solution.

The OCR output is page-separated Markdown. Mathematical notation uses
`$...$` for inline expressions and `$$...$$` for display expressions.

### 5.2 Rebuilding the OCR output

OCR dependencies are separate from application dependencies:

```bash
python -m pip install -r requirements-ingest.txt
curl -L \
  https://www.study4exams.gr/physics_k/pdf/FK_K5_E/FK_K5_E_A.pdf \
  -o FK_K5_E_A.pdf
python ocr_pipeline.py FK_K5_E_A.pdf
```

The pipeline must:

- support resuming after interruption;
- write completed pages atomically;
- retain page boundaries;
- preserve inline and display mathematics where recoverable; and
- make boilerplate removal inspectable.

Ingestion is an offline preparation step. The served application and its
container do not import or install the OCR stack.

### 5.3 Chunk contract

Each corpus record contains a stable `chunk_id` and its source text. Chunking
uses the exercise-and-solution unit rather than a fixed token window. A
`$$...$$` block must remain intact.

The `chunk_id` and text stored in Qdrant are fixed together at index time.
Any corpus or chunking change therefore requires regeneration of embeddings
and a collection rebuild.

---

## 6. Retrieval and generation

### 6.1 Retrieval

- **Encoder:** BGE-M3 through FlagEmbedding.
- **Representation:** dense multilingual embeddings.
- **Store:** Qdrant embedded mode at `./qdrant_data`.
- **Deployed query:** problem statement only.
- **Result:** top-k records containing `chunk_id`, text and similarity score.

BGE-M3 sparse lexical weights are not used by the current collection. Adding
hybrid retrieval would require a new collection schema and an explicit
dense/sparse fusion rule.

### 6.2 Query decision

Problem-only retrieval was originally selected on the hypothesis that errors
in a student attempt could distort the retrieval representation. The
development comparison did not support that hypothesis: combining the problem
and attempt increased Recall@5 from 0.80 to 1.00, including on a case whose
attempt contained incorrect momentum algebra.

Problem-only retrieval remains the deployed baseline for a different reason:
the problem statement is a stable input, while the observed advantage of the
combined query has not yet been tested across varied forms of student work.
The development attempts are relatively articulate and do not represent bare
algebra, ambiguous wording or incorrect terminology adequately. The
implementation therefore remains unchanged, but its rationale has been
revised. Query selection will be revisited after the held-out evaluation.

### 6.3 Prompt construction

The prompt contains:

1. retrieved corpus passages;
2. the closed taxonomy;
3. the problem statement;
4. the student attempt; and
5. output and task instructions.

Corpus passages and user-provided text are delimited as data. Instructions are
placed after the source material. The student attempt is included verbatim for
diagnosis even though it is excluded from the deployed retrieval query.

### 6.4 Generation

Generation uses a hosted frontier model through a provider-specific function.
The system has been exercised with Anthropic and Gemini providers; the public
demonstrator uses the configured provider available at deployment.

The model must:

- compare the attempt with the problem and retrieved material;
- identify the point at which the reasoning diverges;
- cite only retrieved chunk IDs; and
- select candidate labels only from the supplied taxonomy.

---

## 7. Misconception taxonomy

The taxonomy is a closed JSON resource covering momentum-and-collision
misconceptions, including collision, explosion and momentum-conservation
contexts.

- 15 diagnostic labels are organised into four categories.
- `NO_TAG_MATCH` is available when none of the defined labels is appropriate.
- The model may propose one to three labels.
- Labels outside the resource are rejected by the parser.
- A tutor confirms or rejects the proposed labels.

The taxonomy was drafted with LLM assistance from the source corpus and
reviewed against teaching experience. Its current status is suitable for the
demonstrator; a per-label audit against independently observed student errors
remains planned.

---

## 8. Evaluation

### 8.1 Purpose

The evaluation layer serves two distinct purposes:

- verify that the pipeline, metrics and ablation behave reproducibly; and
- compare design choices before a held-out evaluation is introduced.

Development results are not treated as general performance estimates.

### 8.2 Development set

`eval/cases.jsonl` contains 10 cases with:

- a problem and student attempt;
- a manually assigned misconception label;
- manually assigned source-chunk relevance judgements; and
- provenance fields used by the evaluation scripts.

The set has related authorship with the taxonomy, and relevance labels were
formed from a pooled candidate set. It is therefore used for development and
harness verification.

### 8.3 Measures

| Layer | Measure | Interpretation |
|---|---|---|
| Retrieval | Recall@k | Whether a relevant chunk appears in the first `k` results |
| Retrieval | MRR | How early the first relevant chunk appears |
| Diagnosis | Tag accuracy | Whether the candidate output contains the assigned gold label |
| Grounding contract | Citation validity | Whether every cited ID was returned by retrieval |
| Ablation | Retrieval on/off comparison | Whether retrieved context changes the proposed diagnosis |

### 8.4 Current development observations

| Condition | Result |
|---|---:|
| Problem-only retrieval, Recall@5 | 0.80 |
| Problem-only retrieval, MRR | 0.70 |
| Combined problem-and-attempt query, Recall@5 | 1.00 |
| Tag accuracy with retrieval | 10/10 |
| Tag accuracy without retrieval | 9/10 |

In nine cases, retrieval did not change whether the assigned label was
recovered, although it supplied inspectable source material. In one case,
retrieved context changed an incorrect diagnosis to the assigned diagnosis.
These observations describe the development set only.

### 8.5 Held-out evaluation

Primary system-quality claims require an independently constructed held-out
set. Before that evaluation:

- cases must be derived from observed student errors;
- response form must vary deliberately;
- source relevance must be assigned through a corpus-level review rather than
  only from retrieved candidates; and
- prompts, query construction and taxonomy content must be frozen.

The held-out set will be used to compare problem-only, combined-query and
separate-query fusion strategies.

---

## 9. Verification and release criteria

| Requirement | Current state | Verification |
|---|---|---|
| Greek problem-and-attempt input | Implemented | End-to-end demonstration |
| Greek diagnosis and candidate labels | Implemented | Reviewed example cases |
| Retrieved passages displayed | Implemented | Interface audit panel |
| Retrieval on/off ablation | Implemented | Same diagnostic path controlled by one flag |
| Closed-label enforcement | Implemented | Parser tests |
| Citation-ID subset enforcement | Implemented | `validate_citations()` tests |
| Reproducible offline scoring | Implemented | Evaluation runner and scorers |
| Deterministic test layer | Implemented | 19 tests in `tests/test_core.py` |
| Continuous integration | Implemented | `.github/workflows/tests.yml` |
| CPU container | Implemented | Verified application startup from `Dockerfile` |
| Public demonstrator | Implemented | Hugging Face Spaces deployment |
| Held-out performance evaluation | Planned | Protocol in Section 8.5 |

The deterministic tests make no API calls and do not load the embedding model
or vector store. They cover response parsing, taxonomy integrity, citation
validation and evaluation-file invariants.

---

## 10. Operational constraints

### 10.1 Dependency boundaries

- `requirements.txt`: application runtime and deployment.
- `requirements-dev.txt`: deterministic tests and development tooling.
- `requirements-ingest.txt`: OCR and corpus reconstruction.

The container installs runtime dependencies only. `gradio` is pinned
explicitly because a standalone container does not inherit the SDK version
provided by Hugging Face Spaces.

### 10.2 Deployment

The demonstrator is designed for CPU execution and a single-process embedded
Qdrant store. The container runs as a non-root user and layers dependencies
before source code to preserve build caching.

The hosted generation provider requires an API key and is subject to provider
availability, latency and quota limits. Public deployment is a demonstrator,
not an operational service.

### 10.3 Data handling

The application should be tested with synthetic or anonymised student work.
The current interface does not provide an account system, access controls or a
retention policy suitable for identifiable educational records.

---

## 11. Planned work

### Evaluation priorities

1. Construct the held-out set defined in Section 8.5.
2. Review whether each citation directly supports its associated claim.
3. Compare problem-only retrieval, combined retrieval and separate
   problem/attempt searches with rank fusion.
4. Evaluate dense-and-sparse hybrid retrieval with a defined fusion method.

### Taxonomy priorities

1. Audit every label against previously graded student work.
2. Record whether each entry is observed or constructed.
3. Align category descriptions with the full momentum-and-collisions scope.
4. Define an explicit outcome for fully correct work.

### Possible extensions

- citation-selection experiments;
- reranking and query rewriting;
- additional physics chapters;
- tutor confirmation and persistence;
- longitudinal misconception state; and
- a methodology taxonomy for exercise selection.

These items are not commitments of the current implementation.

---

## 12. Decision record

| Date | Decision | Basis |
|---|---|---|
| 2026-07-11 | Use the problem statement as the deployed retrieval query | Initial hypothesis that erroneous attempts could distort the retrieval representation |
| 2026-07-12 | Use a closed JSON taxonomy with `NO_TAG_MATCH` | Deterministic label validation and an explicit unmatched case |
| 2026-07-21 | Maintain a public Hugging Face Spaces demonstrator | Reproducible access without treating the project as a production service |
| 2026-07-23 | Separate development and held-out evaluation roles | Avoid presenting design-set results as performance estimates |
| 2026-07-23 | Retain problem-only retrieval but revise its rationale | The combined query outperformed the deployed query, but its advantage has not been tested across varied response forms |
| 2026-07-24 | Enforce citation IDs as a subset of retrieved IDs | Make source traceability a deterministic invariant |
| 2026-07-24 | Separate runtime, development and ingestion dependencies | Keep deployment independent of the OCR toolchain |
| 2026-07-24 | Add deterministic tests, CI and a CPU container | Verify core contracts without network or model dependencies |

### 12.1 Revisions to earlier positions

Some entries above replaced earlier positions rather than resolving open
questions. They are retained here because the change itself is relevant to
the development record.

| Date | Topic | Earlier position | Revision |
|---|---|---|---|
| 2026-07-12 | Completion criteria | Public deployment and a fixed evaluation set were immediate completion requirements | Both were deferred under deadline pressure and subsequently completed |
| 2026-07-23 | Taxonomy scope | The taxonomy was described as collision-specific | The stated scope was widened to momentum and collisions, matching a corpus that also contains explosion and momentum-conservation problems |
| 2026-07-23 | Retrieval query | Problem-only retrieval was justified by the hypothesis that erroneous attempts could distort retrieval | The development comparison did not support that hypothesis; the implementation was retained on the revised stability rationale pending held-out evaluation |

In the retrieval case, the decision stood; its justification did not.

---

## 13. Authorship

I designed the architecture and developed the system with assistance from LLM
tools, including Claude, ChatGPT and Gemini. I reviewed and tested the
implementation, evaluated the main design choices, audited the misconception
taxonomy, and manually assigned the evaluation labels for misconceptions and
source-chunk relevance.
