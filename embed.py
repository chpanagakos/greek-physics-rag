import json

import numpy as np
import torch
from FlagEmbedding import BGEM3FlagModel

from paths import CHUNKS, EMBEDDINGS, IDS

texts = []
ids = []

with open(CHUNKS, "r", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)
        texts.append(record["text"])
        ids.append(record["id"])

assert (
    len(texts) == 62 and len(ids) == 62
), f"Count mismatch: {len(texts)} texts, {len(ids)} ids (expected 62)."

print(ids[0], ids[-1])

model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=torch.cuda.is_available())
output = model.encode(texts)
embeddings = output["dense_vecs"]
assert embeddings.shape == (
    62,
    1024,
), f"Shape mismatch: {embeddings.shape}, expected (62, 1024)."
print(embeddings.shape)
np.save(EMBEDDINGS, embeddings)

with open(IDS, "w", encoding="utf-8") as f:
    json.dump(ids, f, ensure_ascii=False)
