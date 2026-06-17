"""
ingest_pdfs.py — Main PDF ingestion pipeline.

For each PDF in raw/pdfs/:
  1. Extract text + structured metadata  (extract_pdf.py)
  2. Synthesize a wiki page via Anthropic API
  3. Chunk text + upsert into ChromaDB
  4. Update corpus_index.json

Usage:
  python scripts/ingest_pdfs.py            # ingest new PDFs only
  python scripts/ingest_pdfs.py --force    # re-ingest everything
  python scripts/ingest_pdfs.py --dry-run  # extract only, no API calls
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import chromadb
    import anthropic
except ImportError:
    print("Missing deps: pip install chromadb anthropic pymupdf sentence-transformers")
    sys.exit(1)

# Resolve paths relative to repo root (parent of scripts/)
SCRIPTS_DIR = Path(__file__).parent
REPO_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from extract_pdf import extract, chunk_document, AFIDocument

RAW_PDFS    = REPO_ROOT / "raw" / "pdfs"
WIKI_DIR    = REPO_ROOT / "wiki"
CHROMA_DIR  = REPO_ROOT / "chroma_db"
INDEX_PATH  = REPO_ROOT / "corpus_index.json"

for d in (WIKI_DIR, CHROMA_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Wiki synthesis prompt
# ---------------------------------------------------------------------------

WIKI_SYSTEM = """You are a policy analyst specializing in Air Force doctrine.

Given extracted text from an Air Force Instruction (AFI), produce a wiki page in markdown.
Be concise, factual, and cite section numbers where possible.

STRUCTURE — use exactly these headings:

# {PUB_NUMBER}: {TITLE}

**OPR:** | **Effective:** | **Implements:** | **Supersedes:**

## Purpose & Scope
One paragraph: what this AFI governs and who it applies to.

## Authority & Responsibilities
Bullet list. Each bullet = one role + what they are authorized/required to do.
Format: `- **[Role/Office]:** [authority or responsibility]`

## Key Requirements
Numbered list of the most important compliance obligations in the document.

## Cross-References
- Implements: (list DoDIs/DoDDs)
- Related AFIs: (list AFIs referenced)

## Gaps & Ambiguities
Identify (a) areas where authority assignment seems unclear, (b) topics the title implies
but the text doesn't fully address, (c) potential conflicts with related pubs if apparent.
Write "None identified" if clean.

Keep every section tight. Do not pad. Do not include information not in the source."""


def _wiki_prompt(doc: AFIDocument) -> str:
    # Use first 14k chars of text — covers most pubs fully, trims massive ones
    body = doc.full_text[:14000]

    auth_block = "\n".join(f"- {s}" for s in doc.authority_statements[:25])

    return f"""Publication: {doc.pub_number}
Title: {doc.title}
OPR: {doc.opr}
Effective: {doc.effective_date}
Certified by: {doc.certified_by}
Implements: {', '.join(doc.implements) or 'Not specified in header'}
Supersedes: {', '.join(doc.supersedes) or 'Not specified in header'}
Total pages: {doc.page_count}
Sections parsed: {len(doc.sections)}

--- DOCUMENT TEXT (first 14,000 chars) ---
{body}

--- AUTHORITY STATEMENTS (extracted) ---
{auth_block or '(none extracted)'}

Generate the wiki page now."""


def synthesize_wiki(doc: AFIDocument, client: anthropic.Anthropic) -> str:
    resp = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2500,
        system=WIKI_SYSTEM,
        messages=[{"role": "user", "content": _wiki_prompt(doc)}],
    )
    return resp.content[0].text


# ---------------------------------------------------------------------------
# LLM-based implements extraction (handles any prose format)
# ---------------------------------------------------------------------------

def extract_implements_llm(doc: AFIDocument, client: anthropic.Anthropic) -> list:
    """
    Use Haiku to extract 'Implements' references from any prose format.
    Handles: 'implements DAFPD 36-24', 'implements Air Force Policy Directive 36-21',
             'implements the requirements of HQ AF Mission Directive 1-10', etc.
    """
    import json as _json

    prompt = f"""You are extracting policy references from an Air Force publication header.

Find all directives, instructions, or policy documents that this publication IMPLEMENTS
(not just references or supersedes — only what it formally implements).

Return ONLY a JSON array of strings. Examples:
["DAFPD 36-24"] or ["AFPD 36-21", "DoDI 1400.25"] or []

Do not include explanatory text. Return [] if nothing found.

Publication: {doc.pub_number}
Text (first 1500 chars):
{doc.full_text[:1500]}"""

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = _json.loads(raw)
        return [str(r).strip() for r in result if r] if isinstance(result, list) else []
    except Exception as e:
        print(f"(implements LLM fallback: {e})")
        return doc.implements  # fall back to regex result



# ---------------------------------------------------------------------------
# ChromaDB helpers
# ---------------------------------------------------------------------------

def get_collection(client: chromadb.PersistentClient):
    # Collection name is hard-coded; must match rag.py
    return client.get_or_create_collection(
        name="afi_corpus",
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(collection, doc: AFIDocument) -> int:
    chunks = chunk_document(doc)
    if not chunks:
        return 0

    stem = Path(doc.file_name).stem
    ids        = [f"{stem}__c{i}" for i in range(len(chunks))]
    documents  = [c["text"] for c in chunks]
    metadatas  = [{k: str(v) for k, v in c.items() if k != "text"} for c in chunks]

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


# ---------------------------------------------------------------------------
# Per-file ingest
# ---------------------------------------------------------------------------

def ingest_one(
    pdf_path: Path,
    *,
    anthropic_client: anthropic.Anthropic,
    chroma_collection,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    wiki_path = WIKI_DIR / f"{pdf_path.stem}.md"
    already_done = wiki_path.exists() and INDEX_PATH.exists()

    if already_done and not force:
        print(f"  SKIP  {pdf_path.name} (use --force to re-ingest)")
        return {"status": "skipped", "file": pdf_path.name}

    # Step 1: Extract
    print(f"  EXTRACT  {pdf_path.name} ...", end=" ", flush=True)
    doc = extract(pdf_path)
    print(f"→ {doc.pub_number} | {len(doc.sections)} sections | {len(doc.authority_statements)} auth stmts")

    if dry_run:
        print(f"  DRY-RUN  skipping API calls")
        return {
            "status": "dry_run",
            "file": pdf_path.name,
            "pub_number": doc.pub_number,
            "title": doc.title,
        }

    # Step 1b: LLM-based implements extraction (handles any prose format)
    print(f"  IMPLEMENTS extracting ...", end=" ", flush=True)
    doc.implements = extract_implements_llm(doc, anthropic_client)
    print(f"→ {doc.implements or '(none found)'}")

    # Step 2: Wiki synthesis
    print(f"  WIKI     synthesizing {doc.pub_number} ...", end=" ", flush=True)
    wiki_md = synthesize_wiki(doc, anthropic_client)
    wiki_path.write_text(wiki_md, encoding="utf-8")
    print(f"→ {len(wiki_md)} chars → {wiki_path.name}")

    # Step 3: ChromaDB
    print(f"  CHROMA   chunking + upserting ...", end=" ", flush=True)
    n_chunks = upsert_chunks(chroma_collection, doc)
    print(f"→ {n_chunks} chunks")

    return {
        "status":                  "ok",
        "file":                    pdf_path.name,
        "pub_number":              doc.pub_number,
        "title":                   doc.title,
        "opr":                     doc.opr,
        "effective_date":          doc.effective_date,
        "implements":              doc.implements,
        "supersedes":              doc.supersedes,
        "references":              doc.references,
        "section_count":           len(doc.sections),
        "authority_statement_count": len(doc.authority_statements),
        "chunk_count":             n_chunks,
        "wiki_file":               wiki_path.name,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",   action="store_true", help="Re-ingest already-processed PDFs")
    parser.add_argument("--dry-run", action="store_true", help="Extract only — no API calls, no ChromaDB writes")
    args = parser.parse_args()

    pdf_files = sorted(RAW_PDFS.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {RAW_PDFS}/")
        print("Drop your AFI PDFs there and re-run.")
        sys.exit(0)

    print(f"Found {len(pdf_files)} PDF(s) in {RAW_PDFS}/\n")

    # Init clients
    anthropic_client = anthropic.Anthropic() if not args.dry_run else None
    chroma_client     = chromadb.PersistentClient(path=str(CHROMA_DIR)) if not args.dry_run else None
    collection        = get_collection(chroma_client) if chroma_client else None

    # Load existing index
    index = json.loads(INDEX_PATH.read_text()) if INDEX_PATH.exists() else {}

    ok = skipped = errors = 0

    for pdf in pdf_files:
        print(f"\n[{pdf.name}]")
        try:
            result = ingest_one(
                pdf,
                anthropic_client=anthropic_client,
                chroma_collection=collection,
                force=args.force,
                dry_run=args.dry_run,
            )
            if result["status"] == "ok":
                index[result["pub_number"]] = result
                ok += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ERROR  {pdf.name}: {e}")
            errors += 1

    if not args.dry_run:
        INDEX_PATH.write_text(json.dumps(index, indent=2))

    print(f"\n{'='*50}")
    print(f"Done.  ok={ok}  skipped={skipped}  errors={errors}")
    if not args.dry_run:
        print(f"Corpus index:  {INDEX_PATH}")
        print(f"Wiki pages:    {WIKI_DIR}/")
        print(f"ChromaDB:      {CHROMA_DIR}/")
        print(f"\nNext step:  python scripts/analyze_corpus.py")


if __name__ == "__main__":
    main()
