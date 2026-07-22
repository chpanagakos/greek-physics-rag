# paths.py
from pathlib import Path

REPO = Path(__file__).resolve().parent
DATA = REPO / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"

OCR_MD = INTERIM / "FK_K5_E_A.md"
CLEAN_MD = INTERIM / "FK_K5_E_A.clean.md"
CHUNKS = DATA / "chunks.jsonl"
EMBEDDINGS = DATA / "embeddings.npy"
IDS = DATA / "ids.json"

QDRANT = REPO / "qdrant_data"
TAXONOMY = REPO / "taxonomy.json"
EVAL = REPO / "eval"
