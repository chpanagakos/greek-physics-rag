from paths import CLEAN_MD, OCR_MD

JUNK_WORDS = (
    "ΒΟΗΘΗΜΑΤΑ",
    "ΨΗΦΙ",
    "ΠΑΝΕΛΛΑΔΙΚΩΝ",
    "ΕΚΠΑΙΔΕΥΤΙΚΑ",
    "ΔΙΟΦΑΝΤΟΣ",
    "εκδoσεων",
    "εκδόσεων",
    "εκδοσεών",
    "εκδοσεων",
    "τεχνολογιας",
    "ΤΕΧΥ",
    "OTIT",
    "ΙΤΥΕ",
    "LUCYO",
    "esuo",
    "OJUO",
    "AIOΦANTOS",
    "<!-- page",
    "Ημερομηνία",
    "Επιμέλεια",
    "Επιστημονικός",
)
with open(OCR_MD, encoding="utf-8") as f:
    text = f.read()
lines = text.splitlines()
print(len(lines))

kept = []
for i, line in enumerate(lines):
    if any(w in line for w in JUNK_WORDS):
        continue
    if (
        i + 2 < len(lines)
        and line.strip().isdigit()
        and lines[i + 1].strip() == ""
        and lines[i + 2].strip() == "---"
    ):
        continue
    if line.strip() == "---":
        continue
    kept.append(line)

with open(CLEAN_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(kept))

print(
    f"Cleaned {len(lines)} lines → {len(kept)} kept, {len(lines) - len(kept)} removed. Wrote FK_K5_E_A.clean.md"
)
