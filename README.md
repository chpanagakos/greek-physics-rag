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

A reviewable RAG pipeline for analysing incorrect student solutions to Greek Panhellenic physics problems.

[**Live demo**](https://huggingface.co/spaces/chpanagakos/greek-physics-rag)
·
[**Evaluation**](#evaluation)
·
[**Run locally**](#run-locally)

[![tests](https://github.com/chpanagakos/greek-physics-rag/actions/workflows/tests.yml/badge.svg)](https://github.com/chpanagakos/greek-physics-rag/actions/workflows/tests.yml)

Given a problem and a student's attempted solution, the system retrieves relevant curriculum material, proposes candidate labels from a closed tutor-reviewed taxonomy, and displays the source passages for review. A tutor makes the final determination; the system is a diagnostic aid, not a grader.

Ten worked cases are available in the demo as click-to-fill examples. Each runs the live pipeline rather than replaying a cached result.

**Current scope:** one chapter of the Greek upper-secondary physics curriculum (collisions), 62 indexed chunks, 15 diagnostic labels, and one end-to-end workflow.

**Project status:** public demonstrator, reproducible evaluation harness, 19 deterministic tests in CI, and a Docker build. 

> The public demo sends submitted text to the configured Gemini API. Do not enter names, contact details, or other sensitive student information. The shared free-tier quota may occasionally be exhausted.

## Why this project

Frontier language models can often solve standard Panhellenic physics problems without retrieval. This project addresses a different question: where does a student's attempted solution diverge from an appropriate method, and what evidence can a tutor inspect when reviewing that diagnosis?

The emphasis is therefore not on producing another worked answer. It is on combining a defined diagnostic vocabulary, retrieved course material, structured output, explicit validation, and evaluation of the retrieval and generation stages.

| | |
|--:|:--|
| **Input** | A Greek physics problem and one attempted solution |
| **Output** | A diagnosis, 1–3 candidate labels, and cited source IDs |
| **Human role** | Inspect the retrieved passages and confirm or reject the candidates |
| **Current domain** | Momentum and collisions in Panhellenic upper-secondary physics |

## Pipeline

```text
Greek physics PDFs
    │
    ├─ Surya OCR in math mode
    │  page-separated Markdown + inline LaTeX
    │
    ├─ rule-based cleaning and manual review
    │
    ├─ exercise-level chunking
    │  one exercise + worked solution per chunk
    │
    ├─ BGE-M3 dense embeddings
    │
    └─ Qdrant embedded vector store
           │
problem ───┴─ top-k retrieval
attempt ───── generation prompt
taxonomy ──── Gemini API
                   │
                   ├─ structured diagnosis
                   ├─ candidate taxonomy labels
                   └─ cited retrieved-chunk IDs
                              │
                              └─ schema, label, and citation-ID validation
                                         │
                                         └─ Gradio review interface
```

The problem statement is the deployed retrieval query. The student's attempt is supplied to the generation model but does not currently influence the retrieval vector. The reasoning behind that decision, and the experiment that challenges it, are described under [Evaluation](#evaluation).

## Corpus ingestion

The source material combines Greek prose with dense mathematical notation. General-purpose OCR systems tested during development had difficulty distinguishing Greek language from Greek letters used as variables, including ω, φ, and λ.

The ingestion pipeline uses Surya in math mode, converts `<math>` output to inline LaTeX delimiters, and writes each processed page atomically. Interrupted runs can therefore resume from the page in progress rather than restarting the document.

A subsequent cleaning pass removes publisher boilerplate using positional and word-fingerprint rules. Manual comparison with the source covered all 390 removed lines from an input of 6,976 lines and found them to be boilerplate. The cleaned material is divided into 62 exercise-level chunks.

The source PDF is not redistributed in this repository. It is published by ΙΤΥΕ «Διόφαντος» and is freely available at the link in [Data and licensing](#data-and-licensing); the ingestion pipeline is reproducible against it, and [Rebuilding the corpus from source](#rebuilding-the-corpus-from-source) gives the exact commands. What ships here is the derived material — 62 chunks and the embedded Qdrant collection — so the application runs without re-running OCR.

## Diagnostic taxonomy

The closed taxonomy contains 15 labels in four categories:

- vector and directional errors;
- conservation-law misapplications;
- system or state misidentification;
- algebraic execution.

An additional `NO_TAG_MATCH` outcome allows the model to abstain when none of the defined labels is appropriate.

The taxonomy was drafted with AI assistance from the corpus and subsequently reviewed by the author. It describes solution method as well as physical correctness: for example, `ERR_SYS_ELASTIC_EXCHANGE` can identify a correct but unnecessarily extended solution that overlooks the equal-mass velocity-exchange property.

The generation model can propose labels only from this fixed set. The taxonomy can therefore be reviewed and revised independently of the model used for generation.

## What the code validates

The pipeline distinguishes deterministic contract checks from judgements that still require human review.

| Enforced in code | Left to tutor review |
|---|---|
| Output conforms to the expected JSON structure | Whether the diagnosis is educationally appropriate |
| Every candidate label belongs to the closed taxonomy | Whether the selected label best describes the student's reasoning |
| Every cited ID belongs to the retrieved set | Whether each cited passage actually supports the associated claim |
| Invalid output raises an error before reaching the interface | Whether an alternative interpretation is preferable |

`validate_citations()` enforces that cited IDs are a subset of the retrieved chunk IDs. This prevents fabricated identifiers from reaching the interface; it does not determine semantic support.

## Worked example

**Problem.** Sphere A, with mass $m$ and speed $v$, collides head-on and perfectly inelastically with a stationary sphere B of mass $2m$. Find the post-collision speed.

**Student attempt.** Conserves kinetic energy through the collision and obtains $V = v/\sqrt{3}$.

**Retrieval-enabled output.** Candidate label `ERR_CONSV_KE_PLASTIC`, with a Greek explanation that kinetic energy is not conserved in a perfectly inelastic collision. The output cites `erotisi-35` and `erotisi-36` — two corpus problems that explicitly state a 25% kinetic-energy loss in plastic collisions — and the interface displays both retrieved passages for inspection. The cited claim was verified against the corpus text directly.

**Retrieval-disabled output.** The same candidate label and no citations. This is the common ablation result for textbook-clear errors: retrieval adds inspectable source context without changing the diagnosis. The Evaluation section covers the one case where it did.

## Evaluation

The repository includes a resumable prediction runner and offline scorers for tag accuracy, retrieval quality, query construction, and citation validity.

### Development-set protocol

The current set contains 10 synthetic, AI-generated attempted solutions, covering 10 of the 15 taxonomy labels. Misconception labels and source-chunk relevance were assigned manually under a fixed rule, blind to retrieval rank and chunk identifier.

This is a development set: the taxonomy and cases were produced through related AI-assisted processes, and the relevance pool was formed from the union of the top 10 results under two query configurations. It is useful for validating the harness, comparing design choices, and exposing failure modes; it is not evidence of generalisation.

The planned held-out set will be constructed independently from errors observed in previously graded student work, vary the form and articulateness of the attempts, and use an exhaustive relevance review of the 62-chunk corpus.

### Results

**Candidate-label accuracy**

| Condition | Top-1 | Any match | Mean candidates |
|---|---:|---:|---:|
| Retrieval enabled | 10/10 | 10/10 | 1.20 |
| Retrieval disabled | 9/10 | 9/10 | 1.30 |

**Retrieval quality**

| Metric | @1 | @3 | @5 |
|---|---:|---:|---:|
| Recall: at least one relevant chunk retrieved | 60% | 80% | 80% |
| Full recall: all relevant chunks retrieved | 50% | 50% | 60% |

**MRR:** 0.700

**Citation-ID validity before enforcement:** 17/17 cited IDs belonged to the retrieved set.

### What the evaluation revealed

**Retrieval changed one diagnosis.** In case `c004`, retrieval produced the correct `ERR_SYS_STATE_ID` candidate; without retrieval, that label was absent. The result was stable across three runs per condition. The highest-ranked chunk supplied the fact omitted from the student's attempt.

**Dense retrieval missed a configuration-level distinction.** The two complete Recall@5 misses form a near-minimal pair: a bullet embeds in wood vertically against the floor in one problem and horizontally on a smooth plane in the other. Their surface wording is similar, but momentum conservation applies differently along the collision axis. The retriever identified the topic but confused the configurations, motivating planned hybrid dense and sparse retrieval.

**The alternative query performed better on this set.** Combining the problem and attempt reached Recall@5 of 10/10, compared with 8/10 for the deployed problem-only query. The attempts in this set are uniformly articulate AI-generated prose, so the comparison does not show whether the advantage persists for bare algebra, ambiguous wording, or incorrect terminology. The problem-only query remains deployed until the held-out evaluation covers those forms.

**Valid citation IDs do not guarantee support.** The model cited 55% of the relevant chunks made available by retrieval. In one case, retrieval returned no relevant material, yet the model produced the correct label from parametric knowledge and cited four non-supporting chunks. Citation IDs make that failure inspectable; semantic support remains a human judgement in the current system.

## Design choices

**Exercise-level chunks.** Each chunk contains one exercise and its worked solution. A retrieval result therefore arrives as a complete example with a stable source ID (`erotisi-35`) that a tutor recognises. Step-level chunking remains a future experiment if retrieval metrics justify the additional granularity.

**Frontier generation model.** Retrieval supplies relevant material, but the model must still compare an attempted solution with the worked method and map the divergence to a taxonomy label. Preliminary project testing found smaller models less reliable on this step, particularly with Greek-language input.

**Single-pass pipeline.** The system uses one retrieve → generate → validate pass. This keeps retrieval results, generated output, and validation failures independently inspectable.

**Prompt ordering.** Retrieved passages appear first, task instructions last, and the taxonomy, problem, and attempt occupy the middle. This follows the positional-attention findings reported by Liu et al. in *Lost in the Middle*.

A dated record of scope and design changes is available in [`SPEC.md`](SPEC.md).

## Scope and limitations

- **Domain:** the index covers one chapter of Greek upper-secondary physics. Out-of-scope inputs are not currently detected but will still receive a diagnosis.
- **Retrieval:** the current system uses dense retrieval only. Recall@5 was 0.80 on the development set, including two complete misses.
- **Evaluation:** the reported results come from a 10-case development set. Primary performance estimates are deferred to an independently constructed held-out set.
- **Citation support:** cited IDs are validated against the retrieved set, but semantic support is not verified programmatically.
- **Visual material:** diagrams and graph-sketching tasks are outside the text-and-LaTeX corpus.
- **Input unit:** the validated input format is one problem and one attempted solution. Multi-part questions (Γ1–Γ4) should be submitted separately; combined submissions are outside the validated input format.
- **Human review:** output consists of candidate labels for tutor confirmation. The system is not an autonomous grader.
- **Availability:** the public demo uses a shared Gemini free-tier quota.

## Run locally

### Prerequisite

The embedded Qdrant database is tracked with [Git LFS](https://git-lfs.com). Install and initialise Git LFS before cloning:

```bash
git lfs install
git clone https://github.com/chpanagakos/greek-physics-rag
cd greek-physics-rag
```

If the repository was cloned without Git LFS, run `git lfs pull` before starting the application. Otherwise the Qdrant database will be a pointer file and SQLite will report that it is not a database.

### Application

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=...
python app.py
```

The Gradio interface is served at `http://localhost:7860`.

To rebuild the embedded collection:

```bash
python embed.py
python load_qdrant.py
```

### Rebuilding the corpus from source

> [!NOTE]
> **This step is not required to run the system.** The repository ships the
> derived corpus (62 chunks and the embedded Qdrant collection), so the
> application, the evaluation and the tests all work without this step. Follow
> it **only** to reproduce ingestion end to end: it pulls several GB of OCR
> dependencies, needs a system poppler install, and is slow without a GPU.
>
>**System prerequisite:** `pdf2image` shells out to poppler.
>
>```bash
>sudo apt install poppler-utils        # Debian/Ubuntu
>pip install -r requirements-ingest.txt
>```
>
>Fetch the source document — Physics, upper secondary, Chapter 5 (Collisions),
>published by ΙΤΥΕ «Διόφαντος» and not redistributed here:
>
>```bash
>mkdir -p data/raw data/interim
>curl -L -o data/raw/FK_K5_E_A.pdf \
>  https://www.study4exams.gr/physics_k/pdf/FK_K5_E/FK_K5_E_A.pdf
>```
>
>Then run the pipeline:
>
>```bash
>python ocr_pipeline.py --input data/raw/FK_K5_E_A.pdf --output data/interim
>python clean.py           # boilerplate removal  → FK_K5_E_A.clean.md
>python chunking.py        # exercise-level split → data/chunks.jsonl (62 records)
>python embed.py           # BGE-M3 dense vectors → data/embeddings.npy
>python load_qdrant.py     # rebuilds the embedded collection
>```
>
>OCR is the slow stage: 123 pages at 250 DPI, GPU strongly preferred. Pages are
>written individually and skipped if already present, so an interrupted run
>resumes with `--pages`/`--start-page` or by simply re-running the same command.
>
>Output is not guaranteed to be byte-identical to the shipped corpus: OCR
>results depend on the model version and rendering DPI, so a rebuild may shift
>chunk boundaries and therefore chunk IDs. Rebuild the vector store and the
>evaluation gold labels together if this happens.

### Evaluation

```bash
python eval/run_cases.py
python eval/run_cases.py --no-retrieval
python eval/score_tags.py
python eval/score_retrieval.py
python eval/score_query_construction.py
python eval/score_citations.py
```

The two prediction commands call the configured generation API. The scoring commands run offline over saved predictions, so every reported number is recomputable from the files in the repository without API access.

### Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

The deterministic suite contains 19 tests covering the parser contract, taxonomy integrity, citation-ID validation, and evaluation-file invariants. It runs in CI on every push without API calls or model downloads.

### Docker

```bash
docker build -t greek-physics-rag .
docker run --rm -p 7860:7860 \
  -e GEMINI_API_KEY=... \
  greek-physics-rag
```

The first container start downloads BGE-M3 (approximately 4.5 GB). Mount a volume at `/home/app/.cache/huggingface` to retain the model cache across runs.

## Data and licensing

**Code:** MIT.

**Corpus:** `chunks.jsonl` and the text payloads in the distributed Qdrant collection are derived from Greek upper-secondary physics material published by ΙΤΥΕ «Διόφαντος» under CC BY-NC-SA. The extracted and chunked material is redistributed under the same licence, with attribution to ΙΤΥΕ «Διόφαντος».

The MIT licence does not extend to the corpus.

Source: [study4exams.gr — ΚΕΦΑΛΑΙΟ 5: ΚΡΟΥΣΕΙΣ](https://www.study4exams.gr/physics_k/pdf/FK_K5_E/FK_K5_E_A.pdf)

## Development and authorship

I designed the architecture and developed the system with assistance from LLM tools, including Claude, ChatGPT, and Gemini. I reviewed and tested the implementation, evaluated the main design choices, audited the misconception taxonomy, and manually assigned the evaluation labels for misconceptions and source-chunk relevance. The OCR ingestion module was generated by an LLM assistant and is retained with that provenance recorded here and in the module itself.

## References and components

- **Prompt ordering:** Liu, N. F. et al. (2024), *Lost in the Middle: How Language Models Use Long Contexts*. [arXiv](https://arxiv.org/abs/2307.03172) · [TACL](https://aclanthology.org/2024.tacl-1.9/)
- **Embeddings:** BGE-M3, [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3). Chen, J. et al. (2024), *M3-Embedding*. [arXiv](https://arxiv.org/abs/2402.03216)
- **OCR:** [Surya](https://github.com/datalab-to/surya), used in math mode.
- **Vector store:** [Qdrant](https://github.com/qdrant/qdrant), embedded mode.
- **Interface:** [Gradio](https://github.com/gradio-app/gradio).
- **Generation:** [Gemini API](https://ai.google.dev/), currently `gemini-2.5-flash`; the provider call is isolated to one function.
