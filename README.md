# Team Wiki

An AI-maintained knowledge base for teams. Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Drop documents into `raw/`. Run one command. The LLM reads them, extracts entities and concepts, writes interconnected wiki pages, and keeps everything cross-referenced. Knowledge compounds instead of rotting.

No vector database. No SaaS. No special tooling. Just Python, markdown, and Git.

**Live demo:** https://lindseybruckbauer.github.io/team-wiki/

---

## What it does

- **Ingests** any markdown document and extracts people, projects, technologies, and decisions
- **Writes** interconnected wiki pages automatically — entities, concepts, source summaries
- **Cross-references** everything — every entity page knows which sources mention it
- **Visualizes** the knowledge graph in the browser (no Obsidian required)
- **Answers questions** via a chat assistant that searches the wiki and cites sources
- **Auto-deploys** to GitHub Pages on every push via GitHub Actions
- **Syncs** to SharePoint via OneDrive for non-technical teammates

---

## Prerequisites

- Python 3.9+
- An Anthropic API key — [console.anthropic.com](https://console.anthropic.com)
- Git
- [Obsidian](https://obsidian.md) (optional — for local graph view)

---

## Setup

### 1. Clone the repo

```bash
git clone git@github.com:lindseybruckbauer/team-wiki.git
cd team-wiki
```

### 2. Install dependencies

```bash
pip3 install anthropic python-dotenv mkdocs mkdocs-material fastapi uvicorn
```

If `mkdocs` is not on your PATH after install (common on Mac):

```bash
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Add your API key

```bash
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

The `.env` file is in `.gitignore` — it will never be committed.

### 4. Open in Obsidian (optional)

Obsidian → Open Vault → Open folder as vault → select the `team-wiki` folder.
Install the **Git** community plugin for auto-sync.
Open Graph view (left sidebar) to see the knowledge graph.

---

## Usage

### Ingesting a document

Drop any markdown file into `raw/` and run:

```bash
python3 ingest.py raw/your-document.md
```

The script prints every file it writes. Commit and push when done:

```bash
git add . && git commit -m "Ingest: your-document" && git push
```

GitHub Actions automatically rebuilds the graph and deploys to GitHub Pages.

### Rebuilding the knowledge graph

Run this any time after ingesting new documents:

```bash
python3 build_graph.py
```

This generates `wiki/javascripts/graph.json` from all wikilinks in the wiki.

### Running the chat assistant locally

Open two terminals:

```bash
# Terminal 1 — wiki site
python3 -m mkdocs serve -a 127.0.0.1:8003

# Terminal 2 — query server
python3 -m uvicorn query_server:app --port 8002
```

Open `http://127.0.0.1:8003` and navigate to the Chat page.

### Publishing to SharePoint via OneDrive

Make sure OneDrive is running and syncing. Then:

```bash
python3 -m mkdocs build && cp -r site/ ~/Library/CloudStorage/OneDrive-BOOZALLENHAMILTON/team-wiki/
```

OneDrive syncs the files to SharePoint automatically. Teammates open `index.html` from their synced OneDrive folder.

---

## Repo structure

```
team-wiki/
├── AGENTS.md              # LLM rules and schema
├── ingest.py              # Ingest script — calls Anthropic API
├── query_server.py        # FastAPI query backend for chat
├── build_graph.py         # Generates graph.json from wikilinks
├── mkdocs.yml             # MkDocs config
├── .github/
│   └── workflows/
│       └── deploy.yml     # Auto-deploy to GitHub Pages on push
├── .env                   # API key — never committed
├── raw/                   # Source documents — add yours here
└── wiki/                  # LLM-maintained — do not edit manually
    ├── index.md           # Auto-updated catalog
    ├── log.md             # Append-only activity log
    ├── graph.md           # Knowledge graph page
    ├── chat.md            # Chat assistant page
    ├── javascripts/
    │   ├── chat.js        # Chat UI
    │   ├── graph.js       # D3 force graph
    │   └── graph.json     # Generated graph data
    ├── entities/          # People, projects, teams
    ├── concepts/          # Technologies, methodologies, terms
    └── sources/           # One summary per ingested document
```

---

## How the chat works

Two-step context reduction:

1. Claude reads `wiki/index.md` and selects the most relevant pages (max 5)
2. Claude reads only those pages and answers with inline citations

This keeps the context window small regardless of wiki size — a precursor to full GraphRAG.

---

## Team collaboration

- Anyone clones the repo, adds their `.env`, and can ingest immediately
- **Convention:** always `git pull` before running `ingest.py` to avoid merge conflicts
- No limit on team size
- For multiple teams in the same org, partition the wiki by team folder:

```
wiki/
  team-a/entities/
  team-a/concepts/
  team-b/entities/
  team-b/concepts/
```

The chat assistant searches across all teams automatically.

---

## Roadmap

- [ ] GraphRAG — store entity relationships as a proper graph, cut context per query from ~2500 to ~200 tokens
- [ ] Public query server — deploy `query_server.py` so chat works from any machine
- [ ] GitHub Actions to SharePoint publish via Microsoft Graph API (requires Azure AD app registration)
- [ ] Multi-format intake — Jupyter notebooks, Notion exports, PDFs, meeting transcripts
- [ ] Slack / email intake — drop a message or forward an email to ingest
- [ ] Cross-team discovery — "what other teams are working on X"

---

## Why not Confluence?

Confluence rots because maintenance is manual and nobody does it. This wiki is maintained by the LLM — every cross-reference, every update, every contradiction flag happens automatically on ingest. The human job is to curate sources and ask good questions.

The wiki is also just markdown in Git. You can read it without a browser, diff it like code, and it works with every editor.

---

## Credits

Built on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (April 2026).
