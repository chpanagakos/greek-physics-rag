import json
import re

with open("FK_K5_E_A.clean.md", encoding="utf-8") as f:
    text = f.read()
pat = re.compile(r"^(Ερώτηση|Άσκηση|Πρόβλημα) ([0-9]+\.)", re.MULTILINE)

# for m in pat.finditer(text):
#     print(m.start(), m.group(1), m.group(2))

matches = list(pat.finditer(text))
starts = [m.start() for m in matches]
boundaries = starts + [len(text)]

with open("chunks.jsonl", "w", encoding="utf-8") as f:
    for i in range(len(matches)):
        slug = {"Ερώτηση": "erotisi", "Άσκηση": "askisi", "Πρόβλημα": "provlima"}
        start = boundaries[i]
        end = boundaries[i + 1]
        chunk = text[start:end]
        kind = slug[matches[i].group(1)]
        num = matches[i].group(2).rstrip(".").zfill(2)
        id_ = f"{kind}-{num}"
        record = {"id": id_, "text": chunk.strip()}
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    # print(f"--- chunk {i+1}: {matches[i].group(0)} ({len(chunk)} chars) ---")
    # print(chunk)
