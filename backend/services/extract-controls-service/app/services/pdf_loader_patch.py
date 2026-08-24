"""
pdf_loader_patch.py

STANDALONE PDF LOADER — self-contained, drop-in replacement for whatever
function currently produces your "[LOAD] Attempt 1 / Attempt 2" log lines
inside extraction_runner.py.

WHY THIS FILE EXISTS (root cause, confirmed from your own logs):
  - ISO 27001:2005 PDF: pdfplumber correctly reported "44 pages" and pulled
    clean text -> extraction was accurate.
  - ISO 27001:2013 PDF: pdfplumber incorrectly reported "0 pages" (a known
    pdfplumber limitation on some PDF internal structures — the PDF DOES
    have a real text layer, as your own screenshots show crisp text like
    "A.5.1.1"). Because of the false "0 pages", your code fell back to
    OCR (pdf2image + pytesseract) — OCR "guesses" text from a screenshot
    of each page, and that guessing is what corrupted IDs:
        A.6.1.3 -> A.6.3    (a digit dropped)
        A.11.3.1 -> AI.3.1  ("11" misread as "I")
        9.2(a)/(b)/(c) bullets -> misread as fake IDs "9.2.c" etc.
  - control_extractor.py (the file you kept pasting) never touches PDF
    loading at all — it only receives whatever text this loader hands it.
    Its logic was correct in both runs; the INPUT text was corrupted only
    for the 2013 file, because only the 2013 file went through OCR.

WHAT THIS FIXES:
  Adds a new attempt BETWEEN pdfplumber and OCR: PyMuPDF (fitz), a
  different PDF-parsing library. It frequently succeeds on exactly the
  kind of PDF that makes pdfplumber misreport "0 pages" / near-empty
  text — without ever needing OCR, so no OCR-style corruption occurs.
  OCR remains the LAST resort, only used if both pdfplumber AND PyMuPDF
  fail (i.e. the PDF is genuinely a scanned image with no real text
  layer at all).

WHY THIS IS FULLY DYNAMIC / NOT A HARDCODED FIX:
  - No framework name, version, or control ID appears anywhere below.
  - The only decision rule is a generic "how many usable lines did we
    get" threshold (MIN_ACCEPTABLE_LINES) — this applies identically
    to ANY PDF you ever load: ISO 27001:2005, :2013, :2022, ISO 9001,
    or anything else.
  - ISO 27001:2005 is UNAFFECTED: its pdfplumber attempt already yields
    1534 lines, which clears MIN_ACCEPTABLE_LINES immediately, so this
    file never even calls PyMuPDF or OCR for it — behavior stays
    identical to what you have today.
  - ISO 9001 is UNAFFECTED for the same reason, as long as its
    pdfplumber extraction already succeeds (which your logs suggest it
    does — it's a text PDF, not the "0 pages" case).

INSTALL (once):
    pip install PyMuPDF pdf2image pytesseract --break-system-packages

INTEGRATION — only 2 lines change in extraction_runner.py:
    1) At the top of extraction_runner.py, add:
           from app.services.pdf_loader_patch import load_pdf_document
    2) Wherever you currently do your PDF loading (the block that logs
       "[LOAD] Step 3: Loading document from disk..." and eventually
       calls pdfplumber / OCR), replace that whole block with:
           chunks = load_pdf_document(file_path)
       That's it — this function returns the SAME shape your pipeline
       already expects: a list of text chunks (list[str]), ready to be
       passed straight into `extract_framework_controls(chunks, ...)`
       in control_extractor.py. Nothing downstream needs to change.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Tunables — generic, not tied to any framework/version.
# ---------------------------------------------------------------------

# How many non-empty lines an attempt must produce to be considered
# "successful". Below this, we treat it the same as an outright failure
# (this is what catches pdfplumber's silent "0 pages" case, which raises
# no exception — it just returns almost nothing).
MIN_ACCEPTABLE_LINES = 20

# How many lines go into each returned chunk. This only affects how many
# chunks control_extractor.py's batching sees — it does not affect
# correctness (control_extractor.py's own EXTRACTION_CHUNK_BATCH_SIZE
# batches multiple chunks together regardless of this number).
LINES_PER_CHUNK = 20

# OCR image resolution. Higher = more accurate OCR, slower. Only matters
# for the rare case where a PDF is genuinely a scanned image and OCR is
# unavoidable.
OCR_DPI = 300


def _chunk_lines(lines: list[str], lines_per_chunk: int = LINES_PER_CHUNK) -> list[str]:
    """Group a flat list of lines into chunk strings, same shape your
    pipeline already expects (a list of text blobs)."""
    chunks = []
    for i in range(0, len(lines), lines_per_chunk):
        chunk = " ".join(lines[i : i + lines_per_chunk])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def _pdfplumber_extract(file_path: str) -> list[str]:
    """Attempt 1 — same library/approach you already use."""
    lines: list[str] = []
    try:
        import pdfplumber

        logger.info("[LOAD] Attempt 1: pdfplumber text extraction...")
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            logger.info(f"[LOAD] PDF has {page_count} pages")
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines.extend(text.split("\n"))
    except Exception as e:
        logger.warning(f"[LOAD] pdfplumber attempt failed: {e}")
        return []
    lines = [l for l in lines if l.strip()]
    if lines:
        logger.info(f"[LOAD]  pdfplumber extracted {len(lines)} lines")
    return lines


def _pymupdf_extract(file_path: str) -> list[str]:
    """
    NEW Attempt 1.5 — PyMuPDF (fitz). Different parser than pdfplumber;
    frequently succeeds where pdfplumber reports "0 pages" / near-empty
    text on a PDF that actually DOES have a text layer. This is what
    avoids OCR (and OCR's character-level misreads) for PDFs like your
    ISO 27001:2013 file.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning(
            "[LOAD] PyMuPDF not installed — skipping Attempt 1.5. "
            "Run: pip install PyMuPDF"
        )
        return []

    try:
        logger.info("[LOAD] Attempt 1.5: PyMuPDF (fitz) text extraction...")
        doc = fitz.open(file_path)
        logger.info(f"[LOAD] PyMuPDF reports {doc.page_count} pages")
        lines: list[str] = []
        for page in doc:
            text = page.get_text("text") or ""
            lines.extend(text.split("\n"))
        doc.close()
        lines = [l for l in lines if l.strip()]
        if lines:
            logger.info(f"[LOAD]  PyMuPDF extracted {len(lines)} lines")
        return lines
    except Exception as e:
        logger.warning(f"[LOAD] PyMuPDF attempt failed: {e}")
        return []


def _ocr_extract(file_path: str) -> list[str]:
    """
    Attempt 2 (last resort) — same OCR approach you already use
    (pdf2image + pytesseract), unchanged in method. Only reached when
    BOTH pdfplumber and PyMuPDF fail to produce usable text — i.e. the
    PDF is genuinely a scanned image with no real text layer.
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError as e:
        logger.error(f"[LOAD] OCR dependencies missing: {e}")
        return []

    logger.info("[LOAD] Attempt 2: OCR extraction (pdf2image + pytesseract)...")
    try:
        logger.info("[LOAD] Converting PDF to images...")
        images = convert_from_path(file_path, dpi=OCR_DPI)
        logger.info(f"[LOAD] Converted to {len(images)} images")
    except Exception as e:
        logger.error(f"[LOAD] PDF-to-image conversion failed: {e}")
        return []

    all_lines: list[str] = []
    for i, image in enumerate(images, start=1):
        logger.info(f"[LOAD] OCR scanning page {i}/{len(images)}...")
        try:
            text = pytesseract.image_to_string(image)
            page_lines = [l for l in text.split("\n") if l.strip()]
            all_lines.extend(page_lines)
            logger.info(f"[LOAD] Page {i}: OCR extracted {len(page_lines)} lines")
        except Exception as e:
            logger.warning(f"[LOAD] OCR failed on page {i}: {e}")

    logger.info(f"[LOAD]  OCR extraction complete: {len(all_lines)} total lines")
    return all_lines


def load_pdf_document(file_path: str) -> list:
    """
    Main entry point — call this instead of your current PDF-loading
    code. Returns a list of text chunks, same shape your pipeline
    already expects downstream (extract_framework_controls(chunks, ...)).

    Order: pdfplumber -> PyMuPDF -> OCR. Each step only runs if the
    previous one produced fewer than MIN_ACCEPTABLE_LINES usable lines.
    """
    logger.info(f"[LOAD] Loading document | ext=.pdf | path={file_path}")
    logger.info("[LOAD] Starting PDF extraction...")

    lines = _pdfplumber_extract(file_path)

    if len(lines) < MIN_ACCEPTABLE_LINES:
        logger.info(
            f"[LOAD] pdfplumber yielded only {len(lines)} usable line(s) "
            f"— trying PyMuPDF before falling back to OCR"
        )
        fitz_lines = _pymupdf_extract(file_path)
        if len(fitz_lines) >= MIN_ACCEPTABLE_LINES:
            logger.info(
                f"[LOAD]  Using PyMuPDF result ({len(fitz_lines)} lines) — "
                f"OCR skipped entirely"
            )
            lines = fitz_lines
        else:
            logger.info(
                f"[LOAD] PyMuPDF also yielded only {len(fitz_lines)} line(s) "
                f"— this looks like a genuinely scanned/image-only PDF, "
                f"falling back to OCR"
            )
            lines = _ocr_extract(file_path)

    chunks = _chunk_lines(lines)
    logger.info(f"[LOAD] Loaded {len(lines)} lines into {len(chunks)} chunks")
    return chunks