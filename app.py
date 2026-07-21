"""Gradio UI for greek-physics-rag.

Minimal demo wrapper: problem + attempt in, grounded diagnosis out,
with a retrieval on/off toggle (the ablation demo). All logic lives
in retrieve.py and prompt.py; this file is presentation only.

Run: python app.py  ->  http://localhost:7860
"""

import traceback

import gradio as gr

from examples import EXAMPLES
from prompt import QuotaExceededError, diagnose
from retrieve import retrieve

...


def run_diagnosis(problem: str, attempt: str, use_retrieval: bool):
    """Wire the pipeline to the UI. Never raises: a live demo must
    show errors in the interface, not die in the terminal."""
    if not problem.strip() or not attempt.strip():
        return "—", "—", "Συμπληρώστε και την εκφώνηση και τη λύση.", "—"

    try:
        chunks = retrieve(problem) if use_retrieval else []
        retrieved_display = (
            "\n\n".join(
                f"[{c['chunk_id']}]  (score: {c['score']:.4f})\n{c['text']}"
                for c in chunks
            )
            if chunks
            else "(retrieval off — ablation mode)"
        )

        result = diagnose(problem, attempt, chunks, use_retrieval=use_retrieval)

        tags = ", ".join(result["tags"])
        cited = ", ".join(result["cited_chunk_ids"]) or "(none)"
        return tags, cited, result["justification"], retrieved_display

    except QuotaExceededError:
        return (
            "—",
            "—",
            "Το όριο κλήσεων του API εξαντλήθηκε προσωρινά. "
            "Δοκιμάστε ξανά αργότερα.",
            "—",
        )

    except Exception as e:
        traceback.print_exc()
        return "ERROR", "—", f"{type(e).__name__}: {e}", "—"


with gr.Blocks(title="greek-physics-rag") as demo:
    gr.Markdown(
        "# Διάγνωση παρανοήσεων — Κρούσεις\n"
        "Grounded misconception diagnosis over a Greek physics corpus "
        "(ΚΕΦΑΛΑΙΟ 5: ΚΡΟΥΣΕΙΣ, 62 chunks)."
    )

    with gr.Row():
        with gr.Column():
            problem_in = gr.Textbox(
                label="Εκφώνηση προβλήματος",
                lines=6,
                placeholder="Η εκφώνηση, όπως δίνεται στον μαθητή...",
            )
            attempt_in = gr.Textbox(
                label="Λύση μαθητή (προς διάγνωση)",
                lines=10,
                placeholder="Η προσπάθεια του μαθητή, βήμα προς βήμα...",
            )
            retrieval_toggle = gr.Checkbox(
                label="Retrieval (off = ablation: ίδιο ερώτημα χωρίς σώμα αναφοράς)",
                value=True,
            )
            run_btn = gr.Button("Διάγνωση", variant="primary")

        with gr.Column():
            tags_out = gr.Textbox(label="Υποψήφιες ετικέτες", interactive=False)
            cited_out = gr.Textbox(label="Παραπομπές (chunk IDs)", interactive=False)
            justification_out = gr.Textbox(
                label="Τεκμηρίωση", lines=8, interactive=False
            )

        gr.Examples(
            examples=EXAMPLES,
            inputs=[problem_in, attempt_in],
            label="Παραδείγματα (κλικ για συμπλήρωση)",
            cache_examples=False,
        )

    with gr.Accordion("Ανακτημένα αποσπάσματα (audit)", open=False):
        retrieved_out = gr.Textbox(
            label="Τι είδε το μοντέλο", lines=14, interactive=False
        )

    run_btn.click(
        fn=run_diagnosis,
        inputs=[problem_in, attempt_in, retrieval_toggle],
        outputs=[tags_out, cited_out, justification_out, retrieved_out],
    )

if __name__ == "__main__":
    demo.launch()
