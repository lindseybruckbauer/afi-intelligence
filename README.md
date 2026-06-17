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
- **Chat interface** — natural language queries over the full corpus with source citations

Current corpus: 10 AFIs from the 36-series (Personnel). Target: all 3-series AFIs (31–38).

---

## Using the Site

**Analysis pages** (no setup required):
- [Overlaps & Conflicts](https://lindseybruckbauer.github.io/afi-intelligence/ANALYSIS_overlaps/) — where publications assign conflicting authority
- [Policy Gaps](https://lindseybruckbauer.github.io/afi-intelligence/ANALYSIS_gaps/) — missing coverage and thin DoDI implementation
- [Authority Matrix](https://lindseybruckbauer.github.io/afi-intelligence/ANALYSIS_authority_matrix/) — who can approve what, by publication and section

**Chat** — ask anything about the corpus:
> "Who has authority to approve a waiver under AFI 36-2406?"
> "What overlaps exist between AFI 36-2113 and AFI 36-2109?"
> "What DoDI implementation gaps exist in the 36-series?"

Note: the chat API cold-starts after 15 minutes of inactivity. First response may take 20–30 seconds.

---

## Adding More Publications

```bash
# 1. Drop PDFs into raw/pdfs/
cp path/to/new-afis/*.pdf raw/pdfs/

# 2. Ingest (extract + synthesize + embed)
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/ingest_pdfs.py

# 3. Re-run analysis (improves with larger corpus)
python3 scripts/analyze_corpus.py

# 4. Rebuild home page index
python3 scripts/build_index.py

# 5. Deploy
git add wiki/ chroma_db/
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
├── raw/pdfs/              ← drop source PDFs here (gitignored)
├── scripts/
│   ├── extract_pdf.py     ← PyMuPDF extraction with AF-aware metadata parser
│   ├── ingest_pdfs.py     ← extract → wiki synthesis (Claude Opus) → ChromaDB
│   ├── analyze_corpus.py  ← gap / overlap / authority matrix analysis
│   └── build_index.py     ← regenerates wiki/index.md from corpus_index.json
├── api/
│   ├── main.py            ← FastAPI: /chat and /health endpoints
│   └── rag.py             ← ChromaDB semantic search layer
├── wiki/                  ← MkDocs docs_dir (all generated content)
│   ├── ANALYSIS_*.md      ← cross-publication analysis pages
│   ├── afi36-*.md         ← per-publication wiki pages
│   ├── stylesheets/       ← USAF color theme CSS
│   └── javascripts/       ← chat interface JS
├── chroma_db/             ← local vector store (committed, ~4MB)
├── mkdocs.yml             ← MkDocs Material config
└── render.yaml            ← Render.com API deployment config
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
                     ↓
              ANALYSIS_*.md
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

---

## Known Issues & Debt

| Issue | Severity | Fix |
|-------|----------|-----|
| `Implements: []` on all pubs | Medium | `_list_field()` regex in `extract_pdf.py` |
| AFH/AFGM: 0 sections parsed | Low | These doc types use non-standard structure; falls back to sliding-window chunking |
| Render cold start (~20s) | Low | Upgrade to paid Render tier for production use |
| Chat gives thin answers on specific authority questions | Medium | Chunk size / re-chunking strategy; authority statements need larger context windows |

---

## Roadmap

**Phase 2 — Full 3-Series Corpus**
Acquire and ingest all active AFIs in series 31–38 (~80–150 publications).
The pipeline handles any volume; this is purely an acquisition task.

**Phase 3 — DoDI Cross-Reference Layer**
Cross-walk AFI "Implements" citations against actual DoDI requirements.
Requires fixing `Implements` extraction (see Known Issues) and acquiring DoDI source docs.

**Phase 4 — Knowledge Graph**
Graph layer over the authority chain and cross-reference relationships.
ChromaDB RAG finds semantically similar content but doesn't traverse relationships.
Target: authority delegation chains, DoDI→AFI→supplement hierarchies.

**Phase 5 — SharePoint Native Hosting**
Current delivery: GitHub Pages link from a SharePoint page (no IT approval needed).
Full native hosting requires Azure AD app registration (IT/ISSO approval path).

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Used by ingest, analysis, and chat API |

Set locally: `export ANTHROPIC_API_KEY=sk-ant-...`
Set on Render: Dashboard → Environment → Add Variable

---

## Tech Stack

- **Extraction:** PyMuPDF (`fitz`)
- **Wiki synthesis:** Claude Opus 4.6
- **Vector store:** ChromaDB (local persistent, `all-MiniLM-L6-v2` embeddings)
- **Chat API:** FastAPI + Uvicorn on Render.com
- **Chat model:** Claude Sonnet 4.6
- **Site:** MkDocs Material with USAF color theme
- **Deploy:** GitHub Actions → GitHub Pages + Render auto-deploy
