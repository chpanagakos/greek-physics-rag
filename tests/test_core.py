"""
Deterministic-layer tests: parser contract, taxonomy integrity, eval-file
invariants, citation validity. No API calls, no model loading, no Qdrant.

Run:  pytest tests/ -v
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import CASES_PATH, CHUNKS, TAXONOMY  # noqa: E402
from prompt import load_taxonomy, parse_response  # noqa: E402

TAXO = load_taxonomy()


# ---------------------------------------------------------------------------
# Parser contract — parse_response
# ---------------------------------------------------------------------------

def _payload(tags, justification="δοκιμή", cited=None):
    """Build a valid model-output JSON string; cited=None omits the field."""
    data = {"tags": tags, "justification": justification}
    if cited is not None:
        data["cited_chunk_ids"] = cited
    return json.dumps(data, ensure_ascii=False)


def test_valid_tag_accepted():
    out = parse_response(_payload(["ERR_CONSV_KE_PLASTIC"], cited=["erotisi-35"]), TAXO)
    assert out["tags"] == ["ERR_CONSV_KE_PLASTIC"]


def test_hallucinated_tag_rejected_and_named():
    with pytest.raises(ValueError) as exc:
        parse_response(_payload(["ERR_MADE_UP"], cited=[]), TAXO)
    assert "ERR_MADE_UP" in str(exc.value)


def test_mixed_valid_and_invalid_tags_rejected():
    with pytest.raises(ValueError):
        parse_response(_payload(["ERR_CONSV_KE_PLASTIC", "ERR_FAKE"], cited=[]), TAXO)


def test_empty_tag_list_rejected():
    with pytest.raises(ValueError):
        parse_response(_payload([], cited=[]), TAXO)


def test_no_tag_match_is_a_valid_label():
    out = parse_response(_payload(["NO_TAG_MATCH"], cited=[]), TAXO)
    assert out["tags"] == ["NO_TAG_MATCH"]


def test_malformed_json_raises_with_raw_output_shown():
    with pytest.raises(ValueError) as exc:
        parse_response("{not json", TAXO)
    # The handler prints the rejected input — the debug lesson from 2026-07-12.
    assert "not json" in str(exc.value)


def test_markdown_fenced_json_still_parses():
    fenced = "```json\n" + _payload(["NO_TAG_MATCH"], cited=[]) + "\n```"
    out = parse_response(fenced, TAXO)
    assert out["tags"] == ["NO_TAG_MATCH"]


def test_missing_citations_raises_in_grounded_mode():
    with pytest.raises(ValueError):
        parse_response(_payload(["NO_TAG_MATCH"]), TAXO, require_citations=True)


def test_missing_citations_defaults_empty_in_ablation_mode():
    out = parse_response(_payload(["NO_TAG_MATCH"]), TAXO, require_citations=False)
    assert out["cited_chunk_ids"] == []


# ---------------------------------------------------------------------------
# Citation validity — promoted from observed (17/17 on dev set) to asserted.
# NOTE: this tests a helper that does not exist yet. Write it in prompt.py:
#
#   def validate_citations(cited: list, retrieved_ids: set) -> None:
#       fabricated = [c for c in cited if c not in retrieved_ids]
#       if fabricated:
#           raise ValueError(f"Cited chunk IDs not in retrieved set: {fabricated}")
#
# then call it from diagnose() after parse_response, passing the retrieved
# chunk IDs. That single call changes the README sentence from "not enforced"
# to "enforced".
# ---------------------------------------------------------------------------

def test_citation_within_retrieved_set_accepted():
    from prompt import validate_citations
    validate_citations(["erotisi-01"], {"erotisi-01", "erotisi-02"})


def test_fabricated_citation_rejected_and_named():
    from prompt import validate_citations
    with pytest.raises(ValueError) as exc:
        validate_citations(["erotisi-99"], {"erotisi-01", "erotisi-02"})
    assert "erotisi-99" in str(exc.value)


def test_empty_citations_always_valid():
    from prompt import validate_citations
    validate_citations([], set())


# ---------------------------------------------------------------------------
# Taxonomy integrity — taxonomy.json
# ---------------------------------------------------------------------------

def test_taxonomy_loads_and_flattens():
    assert len(TAXO) >= 15


def test_no_tag_match_present_as_selectable_label():
    assert "NO_TAG_MATCH" in TAXO


def test_every_tag_has_nonempty_description():
    for tag, desc in TAXO.items():
        assert isinstance(desc, str) and desc.strip(), f"Empty description: {tag}"


def test_no_duplicate_tag_ids_across_categories():
    raw = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    seen = []
    for category, body in raw.items():
        seen.append(category) if not body.get("tags") else seen.extend(body["tags"])
    assert len(seen) == len(set(seen))


# ---------------------------------------------------------------------------
# Eval-file invariants — the answer key must not drift from its sources
# ---------------------------------------------------------------------------

def _cases():
    lines = CASES_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(l) for l in lines if l.strip()]


def _corpus_ids():
    ids = set()
    with open(CHUNKS, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ids.add(str(json.loads(line)["id"]))
    return ids


def test_every_gold_tag_exists_in_taxonomy():
    for case in _cases():
        assert case["gold_tag"] in TAXO, f"{case['case_id']}: {case['gold_tag']}"


def test_every_gold_chunk_exists_in_corpus():
    corpus = _corpus_ids()
    for case in _cases():
        for cid in case.get("gold_chunk_ids") or []:
            assert cid in corpus, f"{case['case_id']}: {cid}"


def test_case_ids_unique():
    ids = [c["case_id"] for c in _cases()]
    assert len(ids) == len(set(ids))
