# AFI Policy Intelligence — PDF Pipeline

Extends the Karpathy LLM Wiki prototype to handle Air Force Instructions (PDFs).

## What's new

| File | Purpose |
|------|---------|
| `scripts/extract_pdf.py` | AF-aware PDF extraction (text, metadata, authority statements, sections) |
| `scripts/ingest_pdfs.py` | Main pipeline: extract → wiki synthesis → ChromaDB |
| `scripts/analyze_corpus.py` | Gap, overlap, and authority matrix analysis |
| `api/rag.py` | ChromaDB query layer |
| `api/main.py` | Updated chat API with RAG injection + source citations |

## Setup

```bash
pip install -r requirements.txt
```

ChromaDB downloads a ~90MB embedding model on first run. Works offline after that.

## Workflow

### Step 1: Add PDFs

Drop AFI PDFs into `raw/pdfs/`:
```
raw/pdfs/
  afi31-101.pdf
  afi32-1001.pdf
  afi36-2406.pdf
  ...
```

PDF naming convention: `{pub_slug}.pdf` (e.g., `afi36-2406.pdf`).
The pub number is also extracted from the document header, so exact filename match isn't required.

### Step 2: Test extraction on one file

```bash
python scripts/extract_pdf.py raw/pdfs/afi36-2406.pdf
```

Should print: pub number, title, OPR, section count, authority statement count.

### Step 3: Ingest all PDFs

```bash
# First run (new PDFs only)
python scripts/ingest_pdfs.py

# Re-ingest everything
python scripts/ingest_pdfs.py --force

# Dry run (extract only, no API calls, no ChromaDB writes)
python scripts/ingest_pdfs.py --dry-run
```

This creates:
- `wiki/{afi_slug}.md` — synthesized wiki page per pub
- `chroma_db/` — local ChromaDB (gitignored)
- `corpus_index.json` — structured metadata index

### Step 4: Run analysis

```bash
python scripts/analyze_corpus.py
```

Creates:
- `wiki/ANALYSIS_overlaps.md`
- `wiki/ANALYSIS_gaps.md`
- `wiki/ANALYSIS_authority_matrix.md`

Run a single analysis:
```bash
python scripts/analyze_corpus.py --only matrix
python scripts/analyze_corpus.py --only gaps
python scripts/analyze_corpus.py --only overlaps
```

### Step 5: Start the chat API

```bash
uvicorn api.main:app --reload --port 8000
```

Test:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Who has authority to approve a waiver under AFI 36-2406?"}'
```

### Step 6: Deploy

```bash
mkdocs build
mkdocs gh-deploy
```

## What's gitignored

```
chroma_db/     # vector DB — rebuild from PDFs
raw/pdfs/      # source PDFs — distribute separately
```

## SharePoint delivery (prototype)

1. Deploy to GitHub Pages (existing workflow)
2. Create a SharePoint page → add a "Launch" button/link to the GitHub Pages URL
3. No IT approval needed for the prototype
4. Full SharePoint native hosting: requires Azure AD app registration (IT approval path)

## Environment variables

```bash
export ANTHROPIC_API_KEY=sk-...
```
