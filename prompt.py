"""Prompt assembly and LLM diagnosis for greek-physics-rag.

Builds the diagnosis prompt from (problem, attempt, retrieved chunks,
taxonomy) and calls the frontier LLM. Output is validated against the
closed tag list: the model proposes, the parser disposes.

Block order (Liu et al., "Lost in the Middle"): chunks first and
instructions last occupy the two attention-anchored positions; the
taxonomy and problem/attempt pair ride in the middle, where active
reasoning material survives but passive context would not.
"""

import json
import os
from pathlib import Path

from google import genai
from google.genai import types

# import anthropic


MODEL = "gemini-2.5-flash"
TAXONOMY_PATH = Path(__file__).parent / "taxonomy.json"


def load_taxonomy(path: Path = TAXONOMY_PATH) -> dict[str, str]:
    """Flatten taxonomy.json into {tag_id: description}.

    NO_TAG_MATCH sits at the category level with an empty tags dict;
    it is folded in as an ordinary selectable label so the closed
    list is uniform downstream.
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    flat: dict[str, str] = {}
    for category, entry in raw.items():
        tags = entry.get("tags", {})
        if tags:
            flat.update(tags)
        else:
            # Category with no children (NO_TAG_MATCH) is itself a label.
            flat[category] = entry["description"]
    return flat


def format_chunks(chunks: list[dict]) -> str:
    """Render retrieved chunks with explicit IDs the model must cite."""
    blocks = []
    for c in chunks:
        blocks.append(f"[chunk_id: {c['chunk_id']}]\n{c['text']}")
    return "\n\n".join(blocks)


def format_taxonomy(taxonomy: dict[str, str]) -> str:
    return "\n".join(f"- {tag}: {desc}" for tag, desc in taxonomy.items())


def build_prompt(
    problem: str,
    attempt: str,
    chunks: list[dict],
    taxonomy: dict[str, str],
    use_retrieval: bool = True,
) -> str:
    """Assemble the diagnosis prompt.

    use_retrieval=False omits the chunk block entirely — this is the
    ablation toggle for the demo: same task, no grounding material.
    """
    sections = []

    if use_retrieval and chunks:
        sections.append(
            "ΥΛΙΚΟ ΑΝΑΦΟΡΑΣ (ανακτημένα αποσπάσματα από το σχολικό υλικό):\n\n"
            + format_chunks(chunks)
        )

    sections.append(
        "ΤΑΞΙΝΟΜΙΑ ΣΦΑΛΜΑΤΩΝ (κλειστή λίστα — επίλεξε ΜΟΝΟ από εδώ):\n\n"
        + format_taxonomy(taxonomy)
    )

    sections.append("ΕΚΦΩΝΗΣΗ ΠΡΟΒΛΗΜΑΤΟΣ:\n\n" + problem)

    sections.append("ΛΥΣΗ ΤΟΥ ΜΑΘΗΤΗ (προς διάγνωση):\n\n" + attempt)

    citation_rule = (
        "- Στο justification, στήριξε τη διάγνωση ΑΠΟΚΛΕΙΣΤΙΚΑ στα "
        "ανακτημένα αποσπάσματα, παραθέτοντας τα chunk_id τους στο "
        "cited_chunk_ids. Μην χρησιμοποιείς γνώση εκτός των αποσπασμάτων "
        "για την τεκμηρίωση."
        if use_retrieval and chunks
        else "- Δεν παρέχεται υλικό αναφοράς. Το cited_chunk_ids πρέπει "
        "να είναι κενή λίστα []."
    )

    sections.append(
        "ΟΔΗΓΙΕΣ:\n"
        "Εντόπισε το σφάλμα στη λύση του μαθητή.\n"
        "- Επίλεξε 1 έως 3 υποψήφιες ετικέτες από την κλειστή ταξινομία, "
        "με σειρά πιθανότητας. Αν καμία δεν ταιριάζει, επίλεξε NO_TAG_MATCH "
        "— προτίμησέ το από μια κακή αντιστοίχιση.\n"
        "- Προσοχή: η ετικέτα ERR_SYS_ELASTIC_EXCHANGE αφορά σφάλμα "
        "μεθόδου, όχι ορθότητας — μια σωστή τελική απάντηση ΔΕΝ σημαίνει "
        "αυτόματα NO_TAG_MATCH.\n"
        f"{citation_rule}\n"
        "- Απάντησε ΜΟΝΟ με έγκυρο JSON, χωρίς markdown fences, χωρίς "
        "κείμενο πριν ή μετά, στη μορφή:\n"
        '{"tags": ["TAG_1", ...], "justification": "...", '
        '"cited_chunk_ids": ["...", ...]}\n'
        "Το justification γράφεται στα ελληνικά."
    )

    return "\n\n---\n\n".join(sections)


def parse_response(
    text: str, taxonomy: dict[str, str], require_citations: bool = True
) -> dict:
    # def parse_response(text: str, taxonomy: dict[str, str]) -> dict:
    """Parse and validate the model's JSON. Deterministic gatekeeping:
    hallucinated tags are rejected here, in code, not trusted from the model.

    Raises ValueError with a specific reason on any contract violation.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    # except json.JSONDecodeError as e:
    #     raise ValueError(f"Model output is not valid JSON: {e}") from e
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Model output is not valid JSON: {e}\n"
            f"--- RAW OUTPUT (first 500 chars) ---\n{cleaned[:500]}"
        ) from e

    if not require_citations:
        data.setdefault("cited_chunk_ids", [])

    for field in ("tags", "justification", "cited_chunk_ids"):
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    invalid = [t for t in data["tags"] if t not in taxonomy]
    if invalid:
        raise ValueError(f"Tags not in closed list (rejected): {invalid}")

    if not data["tags"]:
        raise ValueError("Empty tags list; NO_TAG_MATCH exists for this case.")

    return data


def diagnose(
    problem: str,
    attempt: str,
    chunks: list[dict],
    use_retrieval: bool = True,
) -> dict:
    """Full pipeline step: build prompt, call LLM, validate, return dict.

    Returns {"tags": [...], "justification": str, "cited_chunk_ids": [...],
             "prompt": str} — the prompt is included for NOTES.md audits.
    """
    taxonomy = load_taxonomy()
    prompt = build_prompt(problem, attempt, chunks, taxonomy, use_retrieval)

    # client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # response = client.messages.create(
    #     model=MODEL,
    #     max_tokens=1024,
    #     temperature=0,
    #     messages=[{"role": "user", "content": prompt}],
    # )
    # raw_text = response.content[0].text

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=4096,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    raw_text = response.text

    result = parse_response(
        raw_text, taxonomy, require_citations=use_retrieval and bool(chunks)
    )

    # result = parse_response(raw_text, taxonomy)
    result["prompt"] = prompt
    return result


if __name__ == "__main__":
    # Smoke test: wire retrieve.py output straight into diagnose().
    from retrieve import retrieve

    problem = input("Εκφώνηση: ")
    attempt = input("Λύση μαθητή: ")

    chunks = retrieve(problem)  # problem statement only, per locked decision
    result = diagnose(problem, attempt, chunks)

    print("\nTAGS:", result["tags"])
    print("CITED:", result["cited_chunk_ids"])
    print("\n" + result["justification"])
