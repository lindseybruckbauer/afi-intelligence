"""
api/main.py — AFI Policy Intelligence chat API.

Replaces (or extends) the prototype chat API with:
  - ChromaDB RAG context injection
  - Source citation in responses
  - /corpus endpoint for health/stats

Run:
  uvicorn api.main:app --reload --port 8000

Or from repo root:
  uvicorn main:app --reload --port 8000 --app-dir api
"""

import sys
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Make scripts/ importable when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from rag import query as rag_query, format_context, corpus_stats

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="AFI Policy Intelligence API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

_anthropic = anthropic.Anthropic()

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM = """You are an expert assistant for Air Force policy analysis.

You have been given relevant excerpts from Air Force Instructions (AFIs) to help answer the user's question.

Rules:
1. Base your answer on the provided AFI excerpts. Do not guess or fill gaps from general knowledge.
2. Always cite the specific AFI and section (e.g., "AFI 36-2406 §3.2 states...").
3. If two AFIs address the same topic differently, explicitly compare them.
4. If the question cannot be answered from the provided excerpts, say:
   "The corpus doesn't contain enough information on this specific point. The relevant AFIs to check would be [X]."
5. For authority questions: be explicit about WHO has authority, under WHAT conditions, and at WHAT level.
6. Distinguish between SHALL (mandatory), SHOULD (recommended), and MAY (discretionary).

The user may ask about:
- What a specific AFI requires
- Who has authority to approve X
- Where two AFIs overlap or conflict
- What policy gaps exist in a given area
- How to interpret a specific requirement

Keep answers clear and specific. Use bullet points for multi-part answers."""


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str    # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    n_sources: int = 6          # number of RAG chunks to retrieve


class ChatResponse(BaseModel):
    reply: str
    sources: list[dict]         # [{pub_number, section_number, section_title, distance}]
    rag_chunks_used: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # 1. Retrieve relevant context
    chunks = rag_query(req.message, n_results=req.n_sources)
    context = format_context(chunks)

    system_with_ctx = f"{_SYSTEM}\n\n---\nRELEVANT AFI EXCERPTS:\n{context}\n---"

    # 2. Build message history
    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    # 3. Call Anthropic
    try:
        resp = _anthropic.messages.create(
            model="claude-sonnet-4-6",   # sonnet for cost efficiency in chat
            max_tokens=1500,
            system=system_with_ctx,
            messages=messages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anthropic API error: {e}")

    reply = resp.content[0].text

    # 4. Build source list for UI citation
    sources = [
        {
            "pub_number":     c["pub_number"],
            "section_number": c["section_number"],
            "section_title":  c["section_title"],
            "relevance_dist": c["distance"],
        }
        for c in chunks
    ]

    return ChatResponse(
        reply=reply,
        sources=sources,
        rag_chunks_used=len(chunks),
    )


@app.get("/corpus")
def corpus():
    """Returns basic stats about the loaded ChromaDB corpus."""
    return corpus_stats()


@app.get("/health")
def health():
    return {"status": "ok"}
