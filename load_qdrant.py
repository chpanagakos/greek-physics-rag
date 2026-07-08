import json

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

COLLECTION_NAME = "chunks"

embeddings = np.load("embeddings.npy")
texts = []

with open("ids.json", "r", encoding="utf-8") as f:
    ids = json.load(f)

with open("chunks.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)
        texts.append(record["text"])

assert len(texts) == (62), f"Shape mismatch texts: {len(texts)}, expected (62)."
assert len(ids) == (62), f"Shape mismatch ids: {len(ids)}, expected (62)."
assert embeddings.shape[0] == (
    62
), f"Shape mismatch: {embeddings.shape}, expected (62)."

print(len(texts))
print(len(ids))
print(embeddings.shape[0])

client = QdrantClient(path="./qdrant_data")

if client.collection_exists(collection_name=COLLECTION_NAME):
    client.delete_collection(collection_name=COLLECTION_NAME)

client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=embeddings.shape[1], distance=Distance.COSINE),
)

points = []

for i, chunk_id in enumerate(ids):
    point = PointStruct(
        id=i,
        vector=embeddings[i].tolist(),
        payload={"chunk_id": chunk_id, "text": texts[i]},
    )
    points.append(point)

assert len(points) == (62), f"Shape mismatch points"
print(len(points))

operation_info = client.upsert(
    collection_name=COLLECTION_NAME, wait=True, points=points
)
print(operation_info)

print(client.count(collection_name=COLLECTION_NAME))
assert (client.count(collection_name=COLLECTION_NAME).count) == (
    62
), f"Shape mismatch collection count"
