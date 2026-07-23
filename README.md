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

Given a collision problem from the Greek national university-entrance examinations (Panhellenic exams) and a student's incorrect attempt, the system retrieves relevant course material and identifies **candidate misconceptions** from a closed, tutor-audited taxonomy. Its output is intended for tutor review.

**Live demo:** https://huggingface.co/spaces/chpanagakos/greek-physics-rag

The public demonstrator is deployed on Hugging Face Spaces and uses a shared Gemini free-tier quota, so temporary quota exhaustion may occasionally interrupt requests.

Ten worked cases are available as click-to-fill examples; each runs the live pipeline rather than replaying a cached result.

*Privacy:* Inputs are sent to the configured Gemini API for generation. Do not enter student names, contact details or other sensitive information into the public demo.

---

## Purpose and positioning

Frontier language models can often solve standard Panhellenic physics problems without retrieval. This project addresses a different task: analysing a student's attempted solution against a tutor-audited misconception framework and presenting relevant course material alongside the proposed diagnosis.

The intended contribution is a reviewable diagnostic workflow rather than an additional problem-solving interface.

The demo includes an ablation toggle that runs the same case with retrieval enabled or disabled. On the 10-case development set described below, retrieval did not change the correct diagnosis in nine cases, although it provided source material for inspection. In one case, retrieval changed an incorrect diagnosis to the correct one. A separate case shows that visible citations do not by themselves establish evidential support: the model produced the correct tag while citing irrelevant retrieved material. The current system therefore provides an inspectable diagnostic trail, but it does not guarantee citation correctness.

## Corpus ingestion: Greek text and mathematical notation

The corpus is Greek-language physics exam material dense with mathematical notation. The general-purpose OCR systems tested during development performed poorly on this combination: Greek text and Greek-letter math symbols (ω, φ, λ as *variables*, not language) collide constantly.

The ingestion pipeline uses Surya in math mode, converts `<math>` output to inline LaTeX delimiters, and emits page-separated Markdown for subsequent chunking and retrieval.

Pages are rendered, processed and written individually with atomic file operations, allowing interrupted runs to resume from the page in progress. A subsequent cleaning pass removes publisher boilerplate using word-fingerprint and positional rules. Manual comparison with the source covered all 390 removed lines from an input of 6,976 lines and found them to be boilerplate.

## Architecture

```
PDF exam material (Greek)
   │  Surya OCR (math_mode) → Markdown + inline LaTeX
   │  cleaning (rule-based boilerplate removal with manual review)
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

A closed label list for momentum-and-collision misconceptions: 15 tags in four categories (vector/directional errors, conservation-law misapplications, system/state misidentification, algebraic execution), plus an explicit `NO_TAG_MATCH` escape hatch so the model is never forced into a bad fit. The scope matches the corpus, which covers collisions proper alongside explosions and momentum-conservation questions.

**Provenance:** the taxonomy was initially drafted with AI assistance from the corpus and subsequently reviewed by the author. During review, `ERR_SYS_ELASTIC_EXCHANGE` was defined as a *method-efficiency* label for a correct but unnecessarily extended solution to an equal-mass elastic collision. The taxonomy can therefore describe solution method as well as physical correctness. Planned work includes a complete per-label review informed by previously graded student solutions and an explicit outcome for fully correct work.

Example entries:

- `ERR_CONSV_KE_PLASTIC` — student sets K_initial = K_final for a completely inelastic collision
- `ERR_VEC_SUB_SIGN` — sign convention dropped when velocities oppose; Δv computed as v − v instead of v − (−v)
- `ERR_MATH_PCT_BASE` — percentage energy loss computed against the final energy instead of the initial
- `ERR_SYS_ELASTIC_EXCHANGE` — correct result, missed best practice (see above)

The generation model proposes candidate labels from the fixed taxonomy, and a tutor makes the final determination. The parser rejects labels outside the defined set, allowing the taxonomy to be reviewed and revised independently of the model.

## Licence and corpus

**Code** (`*.py`, configuration, `taxonomy.json`): MIT.

**Corpus** (`chunks.jsonl` and the text payloads in the shipped Qdrant collection): derived from Greek upper-secondary physics material published by ΙΤΥΕ «Διόφαντος», licensed CC BY-NC-SA. These files are redistributed here under the same licence, with attribution to ΙΤΥΕ «Διόφαντος» as the original distributor. They are OCR-extracted and chunked, not modified in substance.

The MIT licence does not extend to the corpus material.

## Design decisions

**Frontier model rather than a smaller model.** Retrieval supplies relevant material, but the task still requires comparing a student's attempt with a worked solution and mapping the difference to a taxonomy label. Preliminary project testing found smaller models less reliable on this diagnostic step, particularly with Greek-language input. The interface therefore uses a frontier model and provides an ablation toggle for examining the contribution of retrieval separately.

**Query = problem statement only.** The student's attempt is included verbatim in the generation prompt but not in the retrieval query. On the development set, combining the problem and attempt improved Recall@5 from 80% to 100%. However, those attempts were uniformly articulate, AI-generated prose and may not represent sparse algebra, ambiguous wording or incorrect terminology in real student work. The deployed system retains the more controlled problem-only query pending evaluation on a held-out set with more varied attempts. A possible alternative is to embed the attempt separately and merge the two rankings.

**Prompt block ordering.** Retrieved chunks appear first, task instructions last, and the taxonomy, submitted problem and attempt occupy the middle. This arrangement follows the positional-attention findings reported by Liu et al. and gives prominent positions to the grounding material and citation instructions.

**One exercise + solution per chunk.** Exercises are the corpus's natural retrieval unit: a hit arrives as a complete worked example the diagnosis can cite as a whole, and chunk IDs (`erotisi-35`) map one-to-one to sources a tutor recognizes. Finer granularity (solution-step chunks) is a measured trade-off deferred until retrieval metrics justify it.

**Non-agentic pipeline.** The system uses one retrieve → generate → validate pass. At the current scope, this provides a direct execution path whose retrieval results and structured output can be inspected independently.

## Worked example

Problem: sphere A (mass m, speed v) collides head-on and perfectly inelastically with resting sphere B (mass 2m); find the post-collision speed.

Student attempt: applies conservation of *kinetic energy* through the collision, deriving V = v/√3.

System output (retrieval on): candidate tag `ERR_CONSV_KE_PLASTIC`; justification in Greek stating the student conserved kinetic energy through a plastic collision where energy is necessarily lost; citations `erotisi-35`, `erotisi-36` — two corpus problems that explicitly state a 25% kinetic-energy loss in plastic collisions. The cited claim was verified against the corpus text directly.

Same input, retrieval off (ablation): same tag, no citations. This is the typical ablation outcome on textbook-clear errors; the Evaluation section covers the one case where disabling retrieval changed the diagnosis itself.

## Evaluation

Measured on a 10-case development set (`eval/cases.jsonl`): one (problem, incorrect attempt) pair for each of ten evaluated taxonomy labels. The attempts are synthetic and AI-generated; the gold misconception tags and source chunks were assigned manually under a fixed rule, without reference to retrieval rank or chunk ID. The results are reproducible: `python eval/run_cases.py` produces the predictions, and the `eval/score_*.py` scripts score them offline.

**Tag accuracy** — does the system's first candidate match the hand-assigned tag?

| condition | top-1 | any-match | mean candidates |
|---|---|---|---|
| retrieval on | 10/10 | 10/10 | 1.20 |
| retrieval off (ablation) | 9/10 | 9/10 | 1.30 |

These are development-set results. The taxonomy and cases were produced through related AI-assisted processes, several cases closely resemble their corresponding label descriptions. Each of the ten evaluated labels is represented by a single case; five labels are not yet covered. The current result validates the evaluation pipeline but does not establish generalisation. The next evaluation will use a held-out set derived independently from errors observed in previously graded student work.

**Ablation case study.** With retrieval enabled, case c004 is diagnosed correctly as `ERR_SYS_STATE_ID`; without retrieval, that label is absent from the candidates. The result was consistent across three runs per condition. For the motion described in this case, the highest-ranked retrieved chunk states that the object's velocity at its highest point is zero—the fact omitted from the student's attempt. This is an illustrative case rather than an aggregate result.

**Retrieval quality** — do the top-k chunks include the ones a tutor would need to cite?

| | @1 | @3 | @5 |
|---|---|---|---|
| Recall (≥1 gold chunk retrieved) | 60% | 80% | 80% |
| Full recall (all gold chunks retrieved) | 50% | 50% | 60% |

MRR 0.700. In two cases no gold chunk appears in the top 5.

The two missed cases form a near-minimal pair — a bullet embedding into wood, in one case vertically onto the floor (momentum not conserved on the collision axis), in the other horizontally on a smooth plane (momentum conserved; the error lies elsewhere). The surface text is nearly identical while the physics and the correct tags differ, and the gold chunk for one case was in fact retrieved at rank 2 for the other: the topic is matched but the configuration is not. This quantifies a limitation previously observed anecdotally (a one-word πλαστικά→ελαστικά query swap barely reordering results) and motivates the planned hybrid dense+sparse retrieval using BGE-M3's lexical weights.

**Query construction.** The deployed system embeds only the problem statement. On the development set, a combined problem-and-attempt query achieved Recall@5 of 10/10, compared with 8/10 for the deployed configuration, and recovered both complete misses. Because all attempts in this set are articulate AI-generated prose, the comparison does not cover shorter algebraic responses or misleading terminology. The held-out evaluation will include greater variation in response form before the retrieval query is revised.

**Citation validity and support.** Across the ten retrieval-enabled runs, all 17 cited chunk IDs were present in the retrieved set. The parser currently validates taxonomy labels but does not yet enforce this citation constraint. Citation selection was less complete: the model cited 55% of the gold chunks made available by retrieval. In the vertical-collision case, no relevant chunk was retrieved, yet the model produced the correct label from parametric knowledge and cited four non-supporting chunks. Citation IDs therefore provide inspectable provenance, but the current system does not guarantee that each citation supports the associated claim.

**Protocol note.** Gold chunks were labelled from the union of the top 10 results under two query configurations. Material absent from both result pools could therefore not receive a relevance label, which may make the reported recall optimistic relative to an independently constructed gold set. The held-out evaluation will instead use an exhaustive relevance audit of the 62-chunk corpus.

## Limitations

- **Corpus:** the index contains 62 chunks from one chapter (ΚΕΦΑΛΑΙΟ 5, collisions) of Greek upper-secondary Panhellenic material. Out-of-scope detection has not yet been implemented but still receives a diagnosis.
- **Retrieval:** the current retriever is dense-only. Recall@5 was 0.80 on the development set, including two complete misses involving a configuration-level distinction. Hybrid dense and sparse retrieval remains planned work.
- **Evaluation:** the reported results use a 10-case development set with related authorship between the taxonomy and cases and pooled relevance labelling. A held-out, independently constructed set is required to assess generalisation.
- **Citations:** all cited IDs in the development runs belonged to the retrieved set, although this constraint is not yet enforced programmatically. Whether each citation supports the associated claim remains subject to tutor review.
- **Figures and graphs:** the corpus is text and LaTeX. Questions whose content depends on a diagram, or whose expected answer is a sketched graph, are outside what the system can ground a diagnosis in.
- **Unit of diagnosis:** the input and output schema is designed for one problem and one attempt per submission. Multi-part exam questions (Γ1–Γ4) should be submitted separately; submitted as a single block, the output schema degrades without warning.
- **Quota:** the deployed demo runs on the Gemini free tier, shared across all visitors and exhaustible.
- **Not autonomous:** output is 1–3 *candidate* tags for a tutor to confirm. The system is a diagnostic aid, not a grader.

## Development and authorship

I designed the architecture and made every design decision documented above. Implementation code was written in collaboration with LLM assistants (Claude, ChatGPT, Gemini), with my ownership at the decision, review, and explanation level; I tested the implementation, audited the taxonomy, and manually assigned all evaluation labels.

## Running locally

**Prerequisite: [git-lfs](https://git-lfs.com).** The shipped Qdrant store is a binary tracked with Git LFS. Cloning without git-lfs installed checks out a small pointer text file in its place, and retrieval later fails with `sqlite3.DatabaseError: file is not a database`. Install git-lfs first (`git lfs install`, once per user); if you have already cloned, `git lfs pull` fetches the real file.

```bash
git clone https://github.com/chpanagakos/greek-physics-rag
cd greek-physics-rag
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=...   # provider is isolated to one function; swappable
python app.py               # Gradio UI at localhost:7860

# The Qdrant collection ships with the repo (62 chunks, embedded mode).
# To rebuild it from source instead:
python embed.py        # data/chunks.jsonl → data/embeddings.npy (GPU optional)
python load_qdrant.py  # data/embeddings.npy → local Qdrant collection

# To reproduce the evaluation numbers:
python eval/run_cases.py                    # predictions, retrieval on (API calls)
python eval/run_cases.py --no-retrieval     # ablation condition (API calls)
python eval/score_tags.py                   # tag accuracy (offline)
python eval/score_retrieval.py              # Recall@k, MRR (offline)
python eval/score_query_construction.py     # query experiment (offline)
python eval/score_citations.py              # citation validity (offline)
```

## Status
The end-to-end demonstrator is deployed on Hugging Face Spaces and includes OCR ingestion, preprocessing, chunking, embedding, Qdrant retrieval, structured diagnosis and a Gradio interface with a retrieval ablation toggle. The repository also includes a reproducible evaluation harness covering tag accuracy, Recall@k, MRR, query construction and citation validity on the 10-case development set.

Planned work includes a held-out test set derived from grading experience, deterministic tests for parsing and validation, enforcement of citation validity, and evaluation of hybrid dense and sparse retrieval.

## Scope

The current scope covers one chapter (collisions), one exam family and one diagnostic workflow. It is an evaluated technical demonstrator rather than a complete tutoring platform.

## References and components

**Prompt block ordering** — Liu, N.F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., Liang, P. (2024). *Lost in the Middle: How Language Models Use Long Contexts.* Transactions of the ACL, 12:157–173. [arXiv:2307.03172](https://arxiv.org/abs/2307.03172) · [ACL Anthology](https://aclanthology.org/2024.tacl-1.9/)

**Embeddings** — BGE-M3 ([BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3)). Chen, J., Xiao, S., Zhang, P., Luo, K., Lian, D., Liu, Z. (2024). *M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation.* Findings of the ACL 2024, 2318–2335. [arXiv:2402.03216](https://arxiv.org/abs/2402.03216)

**OCR** — [Surya](https://github.com/datalab-to/surya) (datalab-to), used in math mode for Greek text with inline mathematical notation.

**Vector store** — [Qdrant](https://github.com/qdrant/qdrant), Apache-2.0, run in embedded mode.

**UI** — [Gradio](https://github.com/gradio-app/gradio).

**Generation** — [Gemini API](https://ai.google.dev/) (gemini-2.5-flash). The provider is isolated to a single function; see Design decisions.

**Corpus** — [study4exams.gr — ΚΕΦΑΛΑΙΟ 5: ΚΡΟΥΣΕΙΣ (PDF)](https://www.study4exams.gr/physics_k/pdf/FK_K5_E/FK_K5_E_A.pdf), ΙΤΥΕ «Διόφαντος». See Licence and corpus.
