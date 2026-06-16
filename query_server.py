import os
import json
import re
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()
client = Anthropic()
app = FastAPI()
WIKI_ROOT = Path(__file__).parent

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    question: str

def build_page_map():
    """Map short names to full paths for every .md file in wiki/"""
    page_map = {}
    for p in (WIKI_ROOT / "wiki").rglob("*.md"):
        short = p.stem  # filename without .md
        page_map[short] = p
        page_map[p.name] = p  # with .md
        page_map[str(p.relative_to(WIKI_ROOT))] = p  # full relative path
    return page_map

def read_file(path):
    full = WIKI_ROOT / path
    try:
        return full.read_text()
    except Exception as e:
        print(f"  read_file failed: {full} — {e}")
        return ""

@app.post("/query")
async def query(q: Query):
    index = read_file("wiki/index.md")
    page_map = build_page_map()

    # Step 1: pick relevant pages
    selection_prompt = f"""You are a wiki search assistant.

Here is the wiki index:
{index}

The user asked: {q.question}

Return ONLY a JSON array of the most relevant page names (max 5).
Use the exact names from the index — short names like "Redis", "MayaChen", "2026-05-19-adr-004-wiki-storage".
Example: ["Redis", "MayaChen", "2026-05-19-adr-004-wiki-storage"]
Nothing else. Just the JSON array."""

    selection = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": selection_prompt}]
    )

    raw = selection.content[0].text.strip()
    raw = re.sub(r'```json|```', '', raw).strip()
    print(f"Selected: {raw}")
    match = re.search(r'\[.*?\]', raw, re.DOTALL)
    names = json.loads(match.group()) if match else []

    # Step 2: resolve names to full paths
    context = ""
    resolved = []
    for name in names:
        path = page_map.get(name)
        if path:
            content = path.read_text()
            print(f"  resolved {name} -> {path} ({len(content)} chars)")
            context += f"\n\n--- {name} ---\n{content}"
            resolved.append(str(path.relative_to(WIKI_ROOT)))
        else:
            print(f"  could not resolve: {name}")

    if not context:
        return {"answer": "No relevant wiki pages found.", "sources": []}

    answer_prompt = f"""You are a helpful team knowledge assistant.

Answer the question using only the wiki pages provided below.
Cite sources using [[PageName]] format inline.
Be concise.

WIKI PAGES:
{context}

QUESTION: {q.question}"""

    answer = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": answer_prompt}]
    )

    return {
        "answer": answer.content[0].text,
        "sources": resolved
    }
