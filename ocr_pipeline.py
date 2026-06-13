#!/usr/bin/env python3
"""
OCR Pipeline for Greek Physics Textbooks
Converts PDFs to Markdown with inline LaTeX math.

Usage:
    python ocr_pipeline.py --input ./textbooks/ --output ./corpus/
    python ocr_pipeline.py --input book.pdf --output ./corpus/ --start-page 52 --pages 3
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path

from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
from tqdm import tqdm

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Lazy model loading ────────────────────────────────────────────────────────

_det_predictor = None
_rec_predictor = None


def get_models():
    global _det_predictor, _rec_predictor
    if _det_predictor is None:
        log.info("Loading Surya models...")
        from surya.detection import DetectionPredictor
        from surya.recognition import FoundationPredictor, RecognitionPredictor
        foundation = FoundationPredictor()
        _det_predictor = DetectionPredictor()
        _rec_predictor = RecognitionPredictor(foundation_predictor=foundation)
        log.info("Surya models loaded.")
    return _det_predictor, _rec_predictor


# ── Math tag conversion ───────────────────────────────────────────────────────

def surya_to_markdown(text: str) -> str:
    """Convert Surya XML math tags to Markdown math delimiters."""
    # Block math first
    text = re.sub(
        r'<math display="block">(.*?)</math>',
        lambda m: '\n$$\n' + m.group(1).strip() + '\n$$\n',
        text, flags=re.DOTALL
    )
    # Inline math
    text = re.sub(
        r'<math>(.*?)</math>',
        lambda m: '$' + m.group(1).strip() + '$',
        text, flags=re.DOTALL
    )
    # Bold
    text = re.sub(r'<b>(.*?)</b>', r'**\1**', text)
    # Strip any remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


# ── Page OCR ──────────────────────────────────────────────────────────────────

def ocr_page(image: Image.Image, debug: bool = False) -> str:
    """OCR a single page image, return Markdown string."""
    det, rec = get_models()

    results = rec(
        [image],
        det_predictor=det,
        math_mode=True,
        sort_lines=True,
    )

    result = results[0]
    if not result.text_lines:
        return ""

    md_lines = []
    for line in result.text_lines:
        raw = line.text.strip()
        if not raw:
            continue
        converted = surya_to_markdown(raw)
        if debug:
            log.info("  RAW:  " + repr(raw))
            log.info("  OUT:  " + repr(converted))
        if converted:
            md_lines.append(converted)

    return "\n\n".join(md_lines)


# ── PDF processing ────────────────────────────────────────────────────────────

def _atomic_write(path: Path, text: str) -> None:
    """Write text to path atomically: write to a temp file, then rename.

    os.replace is atomic on POSIX, so an abrupt stop never leaves a
    half-written page file behind — a page file either exists complete
    or not at all. That's what makes resume safe.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _pdf_page_count(pdf_path: Path) -> int:
    """Total pages in the PDF (via poppler's pdfinfo)."""
    return pdfinfo_from_path(str(pdf_path))["Pages"]


def process_pdf(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 250,
    debug: bool = False,
    start_page: int = 1,
    max_pages: int = None,
) -> Path:
    """Process a PDF, writing one Markdown file per page as it completes,
    then stitch them into a single Markdown file.

    Resumable: pages whose per-page file already exists are skipped, so an
    abrupt stop (Colab disconnect, battery sleep, kill) only ever costs the
    page in flight. Rerun the same command to continue where it left off.
    """
    stem = pdf_path.stem
    out_path = output_dir / (stem + ".md")
    pages_dir = output_dir / (stem + ".pages")
    pages_dir.mkdir(parents=True, exist_ok=True)

    # Resolve the page range against the real page count.
    total = _pdf_page_count(pdf_path)
    end_page = min(start_page + max_pages - 1, total) if max_pages else total
    page_range = range(start_page, end_page + 1)

    log.info("Processing " + pdf_path.name + " at " + str(dpi) + " DPI"
             + " (pages " + str(start_page) + "-" + str(end_page)
             + " of " + str(total) + ")")

    done = sum(1 for p in page_range if (pages_dir / f"page_{p:04d}.md").exists())
    if done:
        log.info("  Resuming: " + str(done) + " page(s) already done, "
                 + str(len(page_range) - done) + " to go.")

    for actual_page in tqdm(page_range, desc=pdf_path.name, unit="page"):
        page_file = pages_dir / f"page_{actual_page:04d}.md"

        # Resume: skip any page already written (unless --debug forces redo).
        if page_file.exists() and not debug:
            continue

        # Render only this page — keeps memory flat over a 100+ page run
        # and means a skipped page costs no rendering either.
        images = convert_from_path(
            str(pdf_path), dpi=dpi,
            first_page=actual_page,
            last_page=actual_page,
        )
        page_md = ocr_page(images[0], debug=debug)

        if page_md.strip():
            body = "<!-- page " + str(actual_page) + " -->\n\n" + page_md
        else:
            log.warning("  Page " + str(actual_page) + ": no text extracted.")
            body = "<!-- page " + str(actual_page) + " (empty) -->"

        _atomic_write(page_file, body)

    # Stitch every page file in the dir (in page order) into the final doc.
    page_files = sorted(pages_dir.glob("page_*.md"))
    full_md = "\n\n---\n\n".join(
        f.read_text(encoding="utf-8") for f in page_files
    )
    _atomic_write(out_path, full_md)
    log.info("Written: " + str(out_path) + " (" + str(len(page_files)) + " pages)")
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OCR pipeline: Greek physics PDFs -> Markdown + LaTeX"
    )
    parser.add_argument("--input", "-i", required=True,
                        help="PDF file or directory of PDFs")
    parser.add_argument("--output", "-o", required=True,
                        help="Output directory for Markdown files")
    parser.add_argument("--dpi", type=int, default=250,
                        help="Render DPI (default 250)")
    parser.add_argument("--debug", action="store_true",
                        help="Print raw and converted text for each line")
    parser.add_argument("--start-page", type=int, default=1,
                        help="First page to process, 1-indexed (default 1)")
    parser.add_argument("--pages", type=int, default=None,
                        help="Number of pages to process (default: all)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_dir():
        pdfs = sorted(input_path.glob("*.pdf"))
        if not pdfs:
            log.error("No PDFs found in " + str(input_path))
            sys.exit(1)
        log.info("Found " + str(len(pdfs)) + " PDFs.")
    elif input_path.suffix.lower() == ".pdf":
        pdfs = [input_path]
    else:
        log.error("Input must be a PDF or directory: " + str(input_path))
        sys.exit(1)

    log.info("Loading models...")
    get_models()

    for pdf_path in pdfs:
        log.info("\n" + "=" * 60 + "\n" + pdf_path.name + "\n" + "=" * 60)
        try:
            process_pdf(
                pdf_path, output_dir,
                dpi=args.dpi,
                debug=args.debug,
                start_page=args.start_page,
                max_pages=args.pages,
            )
        except Exception as e:
            log.error("Failed: " + pdf_path.name + ": " + str(e), exc_info=True)

    log.info("Done.")


if __name__ == "__main__":
    main()
