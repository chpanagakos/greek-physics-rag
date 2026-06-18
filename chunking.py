import re

with open("FK_K5_E_A.clean.md", encoding="utf-8") as f:
    text = f.read()
pat = re.compile(r"^(Ερώτηση|Άσκηση|Πρόβλημα) ([0-9]+\.)", re.MULTILINE)

# for m in pat.finditer(text):
#     print(m.start(), m.group(1), m.group(2))

matches = list(pat.finditer(text))
starts = [m.start() for m in matches]
boundaries = starts + [len(text)]

# for i in range(len(matches)):
#     start = boundaries[i]
#     end = boundaries[i + 1]
#     print(repr(text[start:end]))

print(text[boundaries[0] : boundaries[1]])
