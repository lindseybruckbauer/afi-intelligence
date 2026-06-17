"""
extract_pdf.py — Extract text + structured metadata from Air Force publication PDFs.

AF publications have a consistent structure:
  - Header block: number, title, OPR, certified by, supersedes, implements, date
  - Body: numbered paragraphs (1.1., 1.2.1., etc.) — section-aware chunking
  - Attachments: skipped in v1

Run standalone to test a single PDF:
  python extract_pdf.py path/to/afi36-2406.pdf
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF — pip install pymupdf
except ImportError:
    print("Missing dependency: pip install pymupdf")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AFISection:
    number: str        # "1.1.2"
    title: str         # "Responsibilities" (cleaned)
    content: str       # full text from this section header to next
    page_start: int    # 0-indexed page (best-effort)


@dataclass
class AFIDocument:
    # -- Identity --
    pub_number: str              # "AFI 36-2406"
    title: str                   # "OFFICER AND ENLISTED EVALUATION SYSTEMS"
    opr: str                     # "AF/A1P"
    certified_by: str
    supersedes: list             # ["AFI 36-2406, 2 Jan 2014"]
    implements: list             # ["DoDI 1400.25, Vol 431"]
    references: list             # all pub refs found in body
    effective_date: str

    # -- Content --
    full_text: str
    sections: list               # list[AFISection]
    authority_statements: list   # list[str]

    # -- Source --
    file_name: str
    page_count: int


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract(pdf_path: Path) -> AFIDocument:
    doc = fitz.open(str(pdf_path))

    pages = [page.get_text("text") for page in doc]
    full_text = "\n".join(pages)

    # Header lives almost entirely in first 3 pages
    header = "\n".join(pages[:3])

    return AFIDocument(
        pub_number=_pub_number(header, pdf_path.stem),
        title=_title(header),
        opr=_opr(header),
        certified_by=_field(header, r"Certified\s+by\s*:\s*([^\n;(]+)"),
        supersedes=_list_field(header, r"Supersedes\s*:\s*([^\n]+(?:\n[ \t]+[^\n]+)*)"),
        implements=_extract_implements(header),
        references=_all_references(full_text),
        effective_date=_effective_date(header),
        full_text=full_text,
        sections=_parse_sections(full_text),
        authority_statements=_authority_statements(full_text),
        file_name=pdf_path.name,
        page_count=len(doc),
    )


def chunk_document(doc: AFIDocument, max_chars: int = 1800, overlap: int = 200) -> list:
    """
    Produce chunks for ChromaDB.
    Prefer section boundaries; sliding window within oversized sections.
    Returns list of dicts with 'text' and metadata fields.
    """
    chunks = []
    base_meta = {
        "pub_number": doc.pub_number,
        "title":      doc.title,
        "opr":        doc.opr,
        "file_name":  doc.file_name,
    }

    def emit(text, section_number="", section_title="", offset=0):
        if len(text.strip()) < 80:
            return
        chunks.append({
            "text":           text.strip(),
            "section_number": section_number,
            "section_title":  section_title,
            "chunk_offset":   offset,
            **base_meta,
        })

    if doc.sections:
        for sec in doc.sections:
            txt = sec.content
            if len(txt) <= max_chars:
                emit(txt, sec.number, sec.title)
            else:
                for i in range(0, len(txt), max_chars - overlap):
                    emit(txt[i : i + max_chars], sec.number, sec.title, i)
    else:
        # No sections parsed — sliding window on full text
        txt = doc.full_text
        for i in range(0, len(txt), max_chars - overlap):
            emit(txt[i : i + max_chars], offset=i)

    return chunks


# ---------------------------------------------------------------------------
# Private helpers — metadata extraction
# ---------------------------------------------------------------------------

def _pub_number(text: str, filename: str) -> str:
    """
    Extract pub number from header (first 600 chars only — avoids grabbing
    cross-references from the body), then fall back to filename.

    Handles: AFI, AFMAN, AFPD, AFH, DAFI, DAFMAN, DAFH, AFPAM, AFTTP
             AFGM2026-36-2033, DAFGM2025-36-001  (no space before year)
    """
    # Limit to first 600 chars — doc's own number is always in the title block
    header = text[:600]

    # AFGM/DAFGM: AFGM2026-36-2033 (number immediately follows prefix, no space)
    m = re.search(r'\b(AFGM|DAFGM)(\d{4}-\d{2}-\d+)', header, re.IGNORECASE)
    if m:
        return f"{m.group(1).upper()} {m.group(2)}"

    # Standard formats: AFI 36-2406, AFMAN 33-361, DAFI 36-2406, etc.
    m = re.search(
        r'\b(DAFI|AFI|AFMAN|AFPD|AFH|DAFMAN|DAFH|AFPAM|AFTTP)\s+(\d{2}-\d+)',
        header, re.IGNORECASE
    )
    if m:
        return f"{m.group(1).upper()} {m.group(2)}"

    # Filename fallback — standard: afi36-2406.pdf → AFI 36-2406
    m = re.match(
        r'(dafi|afi|afman|afpd|afh|dafman|dafh|afpam|afttp)(\d{2})-(\d+)',
        filename, re.IGNORECASE
    )
    if m:
        return f"{m.group(1).upper()} {m.group(2)}-{m.group(3)}"

    # Filename fallback — AFGM: afgm2026-36-2033.pdf → AFGM 2026-36-2033
    m = re.match(r'(afgm|dafgm)(\d{4}-\d{2}-\d+)', filename, re.IGNORECASE)
    if m:
        return f"{m.group(1).upper()} {m.group(2)}"

    return filename.upper().replace('.PDF', '')


def _title(text: str) -> str:
    """
    Extract the human-readable title from an AF publication.

    Two special cases:
      1. AGFMs: the useful title is the SUBJECT line ("SUBJECT: Guidance Memorandum to...")
      2. Standard AFIs/AFMANs: title follows the pub number + date + series-topic lines

    Root cause of prior bugs:
      - Month filter used abbreviated names (JAN) but AF pubs use full names (JANUARY)
      - in_header trigger fired on body cross-references like "Supersedes: AFI36-2406"
        instead of only the actual pub number line
    Fix: trigger only on lines that START with a recognized pub type prefix.
    """
    # -- AFGM/DAFGM: extract SUBJECT line --
    m = re.search(r'^SUBJECT\s*:\s*(.+)$', text[:2000], re.IGNORECASE | re.MULTILINE)
    if m and re.search(r'\b(AFGM|DAFGM|Guidance Memorandum)', text[:400], re.IGNORECASE):
        return m.group(1).strip()

    lines = [l.strip() for l in text[:2500].splitlines() if l.strip()]

    _FULL_DATE = re.compile(
        r'^\d{1,2}\s+(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST'
        r'|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{4}$',
        re.IGNORECASE,
    )

    # Lines that appear between pub number/date and the actual title
    _NOISE = re.compile(
        r'^(?:PERSONNEL|LOGISTICS|OPERATIONS|COMMUNICATIONS|FINANCIAL|LEGAL'
        r'|TRAINING|SAFETY|MEDICAL|INTELLIGENCE|SUPPLY|TRANSPORTATION'
        r'|ACQUISITION|MANPOWER|SPACE|CYBER|MAINTENANCE|CIVIL ENGINEERING'
        r'|SECURITY FORCES|FORCE MANAGEMENT|NUCLEAR|INFORMATION'
        r'|COMPLIANCE WITH THIS PUBLICATION|ACCESSIBILITY|RELEASABILITY'
        r'|BY ORDER OF|ADMINISTRATIVE|OPR|CERTIFIED|SUPERSEDES|PAGES?\s*:|INCORPORATING'
        r'|CERTIFIED BY|AIR FORCE GUIDANCE).*$',
        re.IGNORECASE,
    )

    in_header = False
    for i, line in enumerate(lines):
        # Trigger ONLY when the line STARTS with a pub type prefix + number.
        # This avoids firing on body references like "Supersedes: AFI36-2406".
        if re.match(
            r'^(?:AIR FORCE|DEPARTMENT OF THE AIR FORCE|DAFI|AFI|AFMAN|AFPD|'
            r'AFH|AFGM|DAFGM|DAFMAN|DAFH|AFPAM|AFTTP)\b',
            line, re.IGNORECASE
        ) and re.search(r'\d{2}[-\s]\d+', line):
            in_header = True
            continue
        if in_header:
            if _FULL_DATE.match(line):
                continue
            if _NOISE.match(line):
                continue
            if len(line) > 8:
                # If short, peek at next line — AF titles often wrap across two lines
                if len(line) < 50 and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if (len(next_line) > 4 and 
                        not _FULL_DATE.match(next_line) and 
                        not _NOISE.match(next_line)):
                        return f"{line} {next_line}"
                return line
    return "Unknown Title"


def _opr(text: str) -> str:
    m = re.search(r'\bOPR\s*:\s*([A-Z0-9/\-]{2,20})', text)
    return m.group(1).strip() if m else "Unknown"


def _field(text: str, pattern: str) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _list_field(text: str, pattern: str) -> list:
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1).replace('\n', ' ')
    # Split on semicolons or commas followed by a pub prefix
    items = re.split(r';\s*|,\s*(?=(?:DAFI|AFI|AFMAN|DoDI|DoDD|AFPD)\s)', raw)
    return [i.strip() for i in items if len(i.strip()) > 3]
def _extract_implements(text: str) -> list:
    """
    AF pubs use prose: 'This publication implements DAFPD 36-24, ...'
    Extract all referenced directives from that sentence.
    """
    refs = []
    m = re.search(
        r'(?:This publication |This instruction )?implements?\s+([^.]{10,400})\.',
        text, re.IGNORECASE
    )
    if m:
        raw = m.group(1)
        for pat in [
            r'(?:DAFI|AFI|AFMAN|AFPD|DAFPD|AFH|DAFMAN)[)\s]+\d{2}-\d+',
            r'\bDoD[ID]\s+\d{4}\.\d+(?:,?\s*Vol(?:ume)?\s*\d+)?',
            r'\bDoDD\s+\d{4}\.\d+',
        ]:
            for hit in re.finditer(pat, raw, re.IGNORECASE):
                refs.append(hit.group(0).strip())
    # header field fallback
    if not refs:
        m2 = re.search(r'Implements\s*:\s*([^\n]+)', text, re.IGNORECASE)
        if m2:
            for pat in [r'\b(?:DAFI|AFI|AFMAN|AFPD|DAFPD)\s+\d{2}-\d+',
                        r'\bDoD[ID]\s+\d{4}\.\d+']:
                for hit in re.finditer(pat, m2.group(1), re.IGNORECASE):
                    refs.append(hit.group(0).strip())
    return sorted(set(r.replace(') ', ' ').strip() for r in refs))

def _effective_date(text: str) -> str:
    m = re.search(
        r'\b(\d{1,2}\s+(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST'
        r'|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{4})\b',
        text, re.IGNORECASE | re.DOTALL
    )
    return m.group(1).upper() if m else ""


def _all_references(text: str) -> list:
    """All publication references mentioned anywhere in the document."""
    refs = set()
    for pattern in [
        r'\b(?:DAFI|AFI|AFMAN|AFPD|AFH|DAFMAN)\s+\d{2}-\d+(?:\s+V\d+)?',
        r'\bDoD[ID]\s+\d{4}\.\d+(?:,?\s*Vol(?:ume)?\s*\d+)?',
        r'\bTitle\s+\d+,?\s*U\.S\.C\.',
    ]:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            refs.add(m.group(0).strip().upper())
    return sorted(refs)


# ---------------------------------------------------------------------------
# Private helpers — content extraction
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(
    r'^'
    r'(\d+(?:\.\d+)+)'     # e.g. "1.1" or "2.3.4"
    r'\.?'                  # optional trailing period
    r'\s{1,4}'              # 1-4 spaces
    r'([A-Z][^\n]{0,120})'  # title starting with capital letter
    r'$',
    re.MULTILINE
)

_CHAPTER_RE = re.compile(
    r'^(Chapter|Section|Attachment)\s+(\d+|[A-Z])\s*[\.\-]?\s*(.*)$',
    re.IGNORECASE | re.MULTILINE
)


def _parse_sections(text: str) -> list:
    """
    Parse numbered sections from the document body.
    AF pubs use: "1.1.  TITLE." pattern.
    Skips attachment sections (usually pure tables / forms).
    """
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        return []

    # Find where attachments start (usually "Attachment 1" or "ATTACHMENT 1")
    attach_match = re.search(r'\nAttachment\s+\d', text, re.IGNORECASE)
    attach_start = attach_match.start() if attach_match else len(text)

    sections = []
    for i, m in enumerate(matches):
        if m.start() > attach_start:
            break
        end = matches[i + 1].start() if i + 1 < len(matches) else attach_start
        content = text[m.start():end].strip()
        if len(content) < 60:
            continue
        sections.append(AFISection(
            number=m.group(1),
            title=m.group(2).strip().rstrip('.').rstrip(),
            content=content,
            page_start=0,
        ))

    return sections


_AUTHORITY_KEYWORDS = re.compile(
    r'(?:is authorized to|may approve|will approve|has authority|'
    r'is responsible for approving|delegates authority|approval authority|'
    r'waiver authority|shall approve|retains authority|grants authority|'
    r'may waive|may grant|has the authority|is the approving authority)',
    re.IGNORECASE
)

# Rough sentence splitter — good enough for policy prose
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z(])')


def _authority_statements(text: str) -> list:
    sentences = _SENT_SPLIT.split(text)
    results = []
    seen = set()
    for sent in sentences:
        sent = sent.strip()
        if not _AUTHORITY_KEYWORDS.search(sent):
            continue
        if len(sent) < 25 or len(sent) > 600:
            continue
        key = sent[:80]
        if key in seen:
            continue
        seen.add(key)
        results.append(sent)
    return results[:120]  # cap per document


# ---------------------------------------------------------------------------
# CLI test harness
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf.py <path/to/file.pdf>")
        sys.exit(1)

    pdf = Path(sys.argv[1])
    doc = extract(pdf)

    print(f"\n{'='*60}")
    print(f"Pub:        {doc.pub_number}")
    print(f"Title:      {doc.title}")
    print(f"OPR:        {doc.opr}")
    print(f"Date:       {doc.effective_date}")
    print(f"Implements: {doc.implements}")
    print(f"Supersedes: {doc.supersedes}")
    print(f"Pages:      {doc.page_count}")
    print(f"Sections:   {len(doc.sections)}")
    print(f"Auth stmts: {len(doc.authority_statements)}")
    print(f"Refs found: {len(doc.references)}")
    print(f"\nFirst 3 sections:")
    for s in doc.sections[:3]:
        print(f"  {s.number}  {s.title[:60]}")
    print(f"\nFirst 2 authority statements:")
    for a in doc.authority_statements[:2]:
        print(f"  - {a[:120]}")

    chunks = chunk_document(doc)
    print(f"\nChunks (for ChromaDB): {len(chunks)}")
