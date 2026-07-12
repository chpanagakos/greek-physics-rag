"""retrieve.py — query the Qdrant collection with a problem statement.

Query construction decision (NOTES.md): the query text is the PROBLEM
STATEMENT ONLY. The student's attempt enters the pipeline later, verbatim,
in the prompt. Rationale: retrieval grounds the diagnosis in authoritative
topical material; embedding erroneous physics risks pulling retrieval
toward the wrong sub-topic.
"""

from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient

QDRANT_PATH = "./qdrant_data"
COLLECTION = "chunks"
DEFAULT_K = 5

# Module-level singletons: loading BGE-M3 is expensive (~2 GB), so both
# the model and the client are created once at import time, not per call.
# use_fp16=False because the laptop is CPU-only.
_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)
_client = QdrantClient(path=QDRANT_PATH)


def embed_query(query_text: str) -> list[float]:
    """Embed a single query string with the SAME treatment embed.py
    used on the corpus: dense_vecs only. Returns a 1024-dim vector."""
    output = _model.encode([query_text])
    return output["dense_vecs"][0].tolist()


def retrieve(query_text: str, k: int = DEFAULT_K) -> list[dict]:
    """Return top-k hits as [{chunk_id, text, score}, ...], best first."""
    vector = embed_query(query_text)
    hits = _client.query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=k,
    ).points
    # If your qdrant-client is older (<1.10) and query_points does not
    # exist, replace the call above with:
    #   hits = _client.search(collection_name=COLLECTION,
    #                         query_vector=vector, limit=k)
    return [
        {
            "chunk_id": hit.payload["chunk_id"],
            "text": hit.payload["text"],
            "score": hit.score,
        }
        for hit in hits
    ]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: python retrieve.py '<problem statement>' [k]")
        sys.exit(1)

    query = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_K

    for rank, hit in enumerate(retrieve(query, k), start=1):
        print(f"{rank}. {hit['chunk_id']}  score={hit['score']:.4f}")
        print(f"   {hit['text'][:120]}...")
        print()
    _client.close()
