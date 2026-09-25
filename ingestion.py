"""
ingestion.py
Turns raw uploaded files (WhatsApp exports, emails, PDFs, notes, calendars,
screenshots) into text chunks with source metadata, and does very light
"entity" extraction (capitalized words, dates) so retrieval can reason about
who/what/when.
"""
import re
import io
from datetime import datetime

from pypdf import PdfReader
from icalendar import Calendar

# --- chunking -----------------------------------------------------------

def chunk_text(text, max_chars=600):
    """Split text into rough paragraph-sized chunks."""
    text = text.strip()
    if not text:
        return []
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        paras = [text]

    chunks = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) < max_chars:
            buf = (buf + "\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks


# --- lightweight entity extraction --------------------------------------

DATE_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
]

def extract_entities(text):
    """Very cheap heuristic: capitalized multi-word phrases as 'people/places',
    plus any dates found. Good enough for a hackathon demo; swap for spaCy/NER
    later if you have time."""
    names = set(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", text))
    # drop common sentence-starters that aren't really entities
    stop = {"The", "This", "That", "There", "They", "It", "We", "I", "You", "He", "She"}
    names = {n for n in names if n.split()[0] not in stop}

    dates = set()
    for pat in DATE_PATTERNS:
        dates.update(re.findall(pat, text))

    return sorted(names)[:8] + sorted(dates)[:4]


def guess_date(text):
    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(0)
    return None


# --- per-type parsers -----------------------------------------------------

def parse_txt(raw_bytes):
    return raw_bytes.decode("utf-8", errors="ignore")


def parse_pdf(raw_bytes):
    reader = PdfReader(io.BytesIO(raw_bytes))
    text = []
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return "\n\n".join(text)


def parse_ics(raw_bytes):
    """Turn calendar events into readable text chunks, one per event."""
    cal = Calendar.from_ical(raw_bytes)
    lines = []
    for component in cal.walk():
        if component.name == "VEVENT":
            summary = str(component.get("summary", ""))
            start = component.get("dtstart")
            start_str = start.dt.isoformat() if start else "unknown date"
            location = str(component.get("location", ""))
            desc = str(component.get("description", ""))
            lines.append(
                f"Calendar event: {summary}\nWhen: {start_str}\nWhere: {location}\nNotes: {desc}"
            )
    return "\n\n".join(lines)


def parse_image(raw_bytes):
    """OCR a screenshot. Requires pytesseract + the tesseract binary installed.
    Fails gracefully if not available."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(raw_bytes))
        return pytesseract.image_to_string(img)
    except Exception as e:
        return f"[OCR unavailable: {e}. Install tesseract-ocr to enable screenshot ingestion.]"


def parse_csv(raw_bytes):
    # treat CSV rows as flat text (e.g. exported calendar/contacts CSV)
    return raw_bytes.decode("utf-8", errors="ignore")


EXT_PARSERS = {
    ".txt": ("note", parse_txt),
    ".md": ("note", parse_txt),
    ".eml": ("email", parse_txt),
    ".pdf": ("pdf", parse_pdf),
    ".ics": ("calendar", parse_ics),
    ".csv": ("calendar", parse_csv),
    ".png": ("screenshot", parse_image),
    ".jpg": ("screenshot", parse_image),
    ".jpeg": ("screenshot", parse_image),
}


def detect_source_type(filename, override=None):
    if override:
        return override
    for ext, (stype, _) in EXT_PARSERS.items():
        if filename.lower().endswith(ext):
            return stype
    return "note"


def parse_file(filename, raw_bytes):
    """Returns raw extracted text for a given uploaded file."""
    for ext, (_, parser) in EXT_PARSERS.items():
        if filename.lower().endswith(ext):
            return parser(raw_bytes)
    # default: try to decode as text
    return parse_txt(raw_bytes)
