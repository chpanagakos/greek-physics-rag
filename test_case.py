"""Smoke test: ERR_CONSV_KE_PLASTIC case, retrieval on vs off."""

import json

from prompt import diagnose
from retrieve import retrieve

problem = (
    "Μια σφαίρα Α μάζας m κινούμενη με ταχύτητα μέτρου v συγκρούεται "
    "κεντρικά και πλαστικά με αρχικά ακίνητη δεύτερη σφαίρα Β διπλάσιας "
    "μάζας (2m). Να βρεθεί η ταχύτητα V του συσσωματώματος αμέσως μετά "
    "την κρούση."
)

attempt = (
    "Εφόσον το σύστημα των δύο σφαιρών είναι μονωμένο, η ενέργεια "
    "διατηρείται. Άρα η αρχική κινητική ενέργεια του συστήματος ισούται "
    "με την τελική κινητική ενέργεια του συσσωματώματος:\n"
    "K_αρχ = K_τελ\n"
    "(1/2)mv^2 = (1/2)(m + 2m)V^2\n"
    "mv^2 = 3mV^2\n"
    "v^2 = 3V^2\n"
    "V = v / sqrt(3)"
)

chunks = retrieve(problem)
print("RETRIEVED:", [c["chunk_id"] for c in chunks], "\n")

print("=== RETRIEVAL ON ===")
on = diagnose(problem, attempt, chunks, use_retrieval=True)
print(
    json.dumps(
        {k: on[k] for k in ("tags", "cited_chunk_ids", "justification")},
        ensure_ascii=False,
        indent=2,
    )
)

print("\n=== RETRIEVAL OFF (ablation) ===")
off = diagnose(problem, attempt, chunks, use_retrieval=False)
print(
    json.dumps(
        {k: off[k] for k in ("tags", "cited_chunk_ids", "justification")},
        ensure_ascii=False,
        indent=2,
    )
)
