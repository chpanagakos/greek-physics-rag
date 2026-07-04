import json

texts = []
ids = []

with open("chunks.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)
        texts.append(record["text"])
        ids.append(record["id"])

assert (
    len(texts) == 62 and len(ids) == 62
), f"Count mismatch: {len(texts)} texts, {len(ids)} ids (expected 62)."

print(ids[0], ids[-1])
