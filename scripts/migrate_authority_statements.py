"""
migrate_authority_statements.py — One-time backfill.

Adds authority_statements to existing corpus_index.json entries
by re-extracting from PDFs locally. No API calls, no wiki regeneration.

Usage:
    python3 scripts/migrate_authority_statements.py
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INDEX_PATH = REPO_ROOT / "corpus_index.json"
RAW_PDFS   = REPO_ROOT / "raw" / "pdfs"

sys.path.insert(0, str(Path(__file__).parent))
from extract_pdf import extract


def main():
    if not INDEX_PATH.exists():
        print("corpus_index.json not found. Run ingest_pdfs.py first.")
        sys.exit(1)

    index = json.loads(INDEX_PATH.read_text())
    updated = skipped = errors = 0

    for pub_num, meta in sorted(index.items()):
        if "authority_statements" in meta:
            print(f"  SKIP  {pub_num} (already has authority_statements)")
            skipped += 1
            continue

        if meta.get("status") == "stub":
            meta["authority_statements"] = []
            updated += 1
            print(f"  STUB  {pub_num} — set to []")
            continue

        pdf_path = RAW_PDFS / meta.get("file", "")
        if not pdf_path.exists():
            print(f"  WARN  {pub_num} — PDF not found at {pdf_path}, setting to []")
            meta["authority_statements"] = []
            updated += 1
            continue

        try:
            doc = extract(pdf_path)
            meta["authority_statements"] = doc.authority_statements
            updated += 1
            print(f"  OK    {pub_num} — {len(doc.authority_statements)} statements extracted")
        except Exception as e:
            print(f"  ERROR {pub_num}: {e}")
            meta["authority_statements"] = []
            errors += 1

    INDEX_PATH.write_text(json.dumps(index, indent=2))
    print(f"\nDone. updated={updated} skipped={skipped} errors={errors}")
    print(f"Corpus index updated: {INDEX_PATH}")


if __name__ == "__main__":
    main()
