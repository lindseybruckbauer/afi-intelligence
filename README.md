# AFI Policy Intelligence

AI-powered gap, overlap, and authority analysis across Air Force Instructions.

**Live site:** https://lindseybruckbauer.github.io/afi-intelligence/
**Chat API:** https://afi-intelligence.onrender.com

> **Disclaimer:** Unofficial tool. Not affiliated with the U.S. Air Force or Department of Defense.
> All source documents are publicly available via [AF e-Publishing](https://www.e-publishing.af.mil).
> Analysis is AI-generated and should be validated against official sources before operational use.

---

## What It Does

Ingests Air Force Instructions (PDFs) and produces:

- **Per-publication wiki pages** — synthesized summaries with authority statements, cross-references, gaps, and key requirements
- **Cross-publication analysis** — overlap findings, policy gaps, and an authority matrix across the full corpus
- **Knowledge graph** — force-directed graph of publication relationships (implements, references, supersedes)
- **Chat interface** — natural language queries with graph-augmented retrieval and source citations

Current corpus: 20 publications across the 31-series (Security Forces) and 36-series (Personnel). Target: all 3x-series AFIs (31-38).

---

## Using the Site

**Analysis pages** (no setup required):
- [Overlaps & Conflicts](https://lindseybruckbauer.github.io/afi-intelligence/ANALYSIS_overlaps/) — where publications assign conflicting authority
- [Policy Gaps](https://lindseybruckbauer.github.io/afi-intelligence/ANALYSIS_gaps/) — missing coverage and thin DoDI implementation
- [Authority Matrix](https://lindseybruckbauer.github.io/afi-intelligence/ANALYSIS_authority_matrix/) — who can approve what, by publication and section
- [Knowledge Graph](https://lindseybruckbauer.github.io/afi-intelligence/graph/) — interactive relationship graph

**Chat** — ask anything about the corpus:
> "Who has authority to approve a waiver under AFI 36-2406?"
> "What AFIs implement DAFPD 36-21?"
> "What DoDI implementation gaps exist in the 36-series?"

---

## Adding More Publications

```bash
# 1. Drop PDFs into raw/pdfs/
cp path/to/new-afis/*.pdf raw/pdfs/

# 2. Ingest (extract + synthesize + embed)
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/ingest_pdfs.py

# 3. Re-run analysis
python3 scripts/analyze_corpus.py

# 4. Rebuild home page index and publications page
python3 scripts/build_index.py
python3 scripts/build_publications.py
python3 build_graph.py

# 5. Deploy
git add wiki/ chroma_db/ corpus_index.json
git commit -m "Add [X] publications"
git push
```

PDF naming: `afi36-2406.pdf`, `afman33-361.pdf`, `afgm2026-36-2033.pdf` etc. The pub number is
also extracted from the document header so exact naming is not required.

---

## Local Development

**Requirements:** Python 3.9+, an Anthropic API key

```bash
git clone https://github.com/lindseybruckbauer/afi-intelligence
cd afi-intelligence
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

# Run chat API locally
uvicorn api.main:app --port 8001

# Serve docs locally (separate terminal)
mkdocs serve
# → http://localhost:8000
```

For local chat, update the API_URL in `wiki/javascripts/chat.js` to `http://127.0.0.1:8001`.

---

## Architecture

```
afi-intelligence/
├── raw/pdfs/                        ← drop source PDFs here (gitignored)
├── scripts/
│   ├── extract_pdf.py               ← PyMuPDF extraction with AF-aware metadata parser
│   ├── ingest_pdfs.py               ← extract → wiki synthesis (Claude Opus) → ChromaDB
│   ├── analyze_corpus.py            ← gap / overlap / authority matrix analysis
│   ├── build_index.py               ← regenerates wiki/index.md from corpus_index.json
│   ├── build_publications.py        ← generates wiki/publications.md
│   ├── run_pipeline.py              ← full pipeline orchestrator
│   └── migrate_authority_statements.py ← one-time backfill (run after updating ingest)
├── build_graph.py                   ← knowledge graph builder
├── api/
│   ├── main.py                      ← FastAPI: /chat, /feedback, /health endpoints
│   └── rag.py                       ← ChromaDB semantic + graph-augmented retrieval
├── wiki/                            ← MkDocs docs_dir (all generated content)
│   ├── ANALYSIS_*.md                ← cross-publication analysis pages
│   ├── afi36-*.md                   ← per-publication wiki pages
│   ├── publications.md              ← auto-generated publications index
│   ├── stylesheets/                 ← USAF color theme CSS
│   └── javascripts/
│       ├── chat.js                  ← chat UI (localStorage persistence, DOMPurify)
│       ├── graph.js                 ← D3 force graph
│       ├── graph.json               ← graph data (auto-generated)
│       └── graph_index.json         ← adjacency list for graph RAG traversal
├── chroma_db/                       ← local vector store (committed, ~4MB)
├── corpus_index.json                ← structured metadata index
├── mkdocs.yml                       ← MkDocs Material config
└── render.yaml                      ← Render deployment config
```

**Data flow:**
```
PDF → extract_pdf.py → AFIDocument
                     ↓                    ↓
              wiki synthesis         chunk + embed
              (Claude Opus)          (ChromaDB)
                     ↓                    ↓
              wiki/{slug}.md       chroma_db/ (committed)
                     ↓                    ↓
              analyze_corpus.py    api/rag.py → /chat endpoint
                     ↓                         (semantic + graph RAG)
              ANALYSIS_*.md
                     ↓
              build_graph.py → graph.json + graph_index.json
```

**Deploy flow:**
- `git push main` → GitHub Actions → MkDocs build → GitHub Pages
- Same push → Render auto-redeploy of FastAPI backend
- ChromaDB is committed to the repo; Render uses it directly (no re-ingest on deploy)

---

## Key Scripts

| Script | What it does | When to run |
|--------|-------------|-------------|
| `ingest_pdfs.py` | Extract + synthesize + embed all PDFs in `raw/pdfs/` | After adding new PDFs |
| `ingest_pdfs.py --force` | Re-ingest everything (overwrites existing wiki pages) | After changing extraction logic |
| `ingest_pdfs.py --dry-run` | Extract only, no API calls | Testing extraction on new pub types |
| `analyze_corpus.py` | Run all three analyses | After ingest or adding pubs |
| `analyze_corpus.py --only gaps` | Run single analysis | Faster iteration |
| `build_index.py` | Regenerate home page | After any ingest or analysis |
| `build_graph.py` | Rebuild knowledge graph | After ingest |
| `migrate_authority_statements.py` | Backfill authority_statements into corpus_index | Run once after upgrading ingest |

---

## Known Issues & Debt

| Issue | Severity | Notes |
|-------|----------|-------|
| `DAFI 31-118` implements itself | Low | Self-reference in header extraction; cosmetic only |
| `AFI 36-2109` implements empty | Low | Admin change overlay obscures header |
| `afji31-213_cover_letter` in nav | Low | Filename cleanup needed |
| Graph node overlap on small corpus | Low | Force simulation needs tuning for fewer than 25 nodes |
| Rate limiter resets on cold start | Low | In-memory only; Redis-backed for production scale |
| No CSP headers | Medium | GitHub Pages cannot set headers; needs CloudFront on AWS |

---

## Roadmap

**Next — Corpus Expansion**
Acquire and ingest AFIs in series 32 (Civil Engineering) and 33 (Communications).
The pipeline handles any volume; this is purely an acquisition task.

**Full 3x-Series Corpus**
All active AFIs in series 31-38 (~80-150 publications).

**DoDI Cross-Reference Layer**
Cross-walk AFI "Implements" citations against actual DoDI requirements.
Requires acquiring DoDI source documents.

**AWS Production Architecture**
```
S3 + CloudFront       → static site (replaces GitHub Pages, adds CSP headers)
API Gateway + ECS     → FastAPI (replaces Render)
S3                    → PDF storage (replaces raw/pdfs/ in repo)
Secrets Manager       → API keys
OpenSearch            → vector store (replaces ChromaDB)
CloudWatch            → audit logging + alerts
```

---

## Environment Variables

| Variable | Required | Where | Description |
|----------|----------|-------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Local + Render | Ingest, analysis, and chat API |
| `AIRTABLE_API_KEY` | Yes (feedback) | Render | Airtable personal access token |
| `AIRTABLE_BASE_ID` | Yes (feedback) | Render | Base ID from Airtable URL (appXXXXX) |
| `AIRTABLE_TABLE_NAME` | Yes (feedback) | Render | Table ID or name (e.g. tblXXXXX) |

Set locally: `export ANTHROPIC_API_KEY=sk-ant-...`
Set on Render: Dashboard → Environment → Add Variable

---

## Tech Stack

- **Extraction:** PyMuPDF (`fitz`)
- **Wiki synthesis:** Claude Opus 4.6
- **Vector store:** ChromaDB (local persistent, `all-MiniLM-L6-v2` embeddings)
- **Graph RAG:** custom 1-hop traversal via `graph_index.json`
- **Chat API:** FastAPI + Uvicorn on Render.com (Starter tier)
- **Chat model:** Claude Sonnet 4.6
- **Feedback storage:** Airtable (via REST API from backend)
- **Site:** MkDocs Material with USAF color theme
- **Deploy:** GitHub Actions → GitHub Pages + Render auto-deploy
