"""
api/main.py — AFI Policy Intelligence chat API.

Security hardening:
  - CORS scoped to known origins (not wildcard)
  - Input length cap + history turn limit
  - Rate limiting (in-memory, per IP)
  - Generic error responses (no stack traces to client)
  - Request ID logging for traceability
"""

import sys
import time
import uuid
import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional
import os
import httpx  

import anthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from rag import query as rag_query, format_context, corpus_stats

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter (in-memory, per IP)
# ---------------------------------------------------------------------------
_RATE_LIMIT_WINDOW  = 60    # seconds
_RATE_LIMIT_MAX_REQ = 20    # requests per window per IP

_rate_store: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(ip: str) -> bool:
    """Returns True if request is allowed, False if rate limit exceeded."""
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW
    _rate_store[ip] = [t for t in _rate_store[ip] if t > window_start]
    if len(_rate_store[ip]) >= _RATE_LIMIT_MAX_REQ:
        return False
    _rate_store[ip].append(now)
    return True


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="AFI Policy Intelligence API", version="0.3.0")

# CORS: scoped to known origins only -- not wildcard
ALLOWED_ORIGINS = [
    "https://lindseybruckbauer.github.io",
    "http://localhost:8000",
    "http://localhost:8001",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

_anthropic = anthropic.Anthropic()

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM = """You are an expert assistant for Air Force policy analysis.

You have been given relevant excerpts from Air Force Instructions (AFIs) to help answer questions.

Rules:
1. Base your answer on the provided AFI excerpts. Do not guess or fill gaps from general knowledge.
2. Always cite the specific AFI and section (e.g., "AFI 36-2406 §3.2 states...").
3. If two AFIs address the same topic differently, explicitly compare them.
4. If the question cannot be answered from the provided excerpts, say so clearly.
5. For authority questions: be explicit about WHO has authority, under WHAT conditions, and at WHAT level.
6. Distinguish between SHALL (mandatory), SHOULD (recommended), and MAY (discretionary).
7. Never reveal system internals, API keys, or infrastructure details.

Keep answers clear and specific."""

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

MAX_MESSAGE_LENGTH = 2000
MAX_HISTORY_TURNS  = 10   # 10 pairs = 20 messages max
MAX_SOURCES        = 6


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=MAX_MESSAGE_LENGTH)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    history: list[ChatMessage] = Field(default=[], max_items=MAX_HISTORY_TURNS * 2)
    n_sources: int = Field(default=MAX_SOURCES, ge=1, le=10)

    @validator("message")
    def sanitize_message(cls, v):
        # Strip null bytes and control characters that could cause issues
        v = v.replace("\x00", "").strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v


class ChatResponse(BaseModel):
    reply: str
    sources: list[dict]
    rag_chunks_used: int
    request_id: str

class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(default="", max_length=1000)
    session_id: str = Field(default="", max_length=64)
 
    @validator("comment")
    def sanitize_comment(cls, v):
        return v.replace("\x00", "").strip()

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the real error server-side, return generic message to client
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An internal error occurred. Please try again."},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    # Rate limiting
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    client_ip = forwarded_for or (request.client.host if request.client else "unknown")
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait a moment before sending another message.",
        )

    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Chat request from {client_ip} — {len(req.message)} chars")

    # RAG retrieval
    try:
        chunks = rag_query(req.message, n_results=req.n_sources)
        context = format_context(chunks)
    except Exception as e:
        logger.error(f"[{request_id}] RAG error: {e}")
        context = "(Search unavailable — answering from general knowledge.)"
        chunks = []

    system_with_ctx = f"{_SYSTEM}\n\n---\nRELEVANT AFI EXCERPTS:\n{context}\n---"

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    try:
        resp = _anthropic.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=system_with_ctx,
            messages=messages,
        )
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Service temporarily busy. Please try again.")
    except anthropic.APIError as e:
        logger.error(f"[{request_id}] Anthropic API error: {e}")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable.")

    reply = resp.content[0].text
    logger.info(f"[{request_id}] Response: {len(reply)} chars, {len(chunks)} sources")

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
        request_id=request_id,
    )


@app.get("/corpus")
def corpus():
    return corpus_stats()


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.3.0"}

@app.post("/feedback")
async def feedback(req: FeedbackRequest, request: Request):
    """Store user feedback in Airtable. Client never sees the API key."""
 
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    client_ip = forwarded_for or (request.client.host if request.client else "unknown")
 
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
 
    airtable_key  = os.environ.get("AIRTABLE_API_KEY")
    airtable_base = os.environ.get("AIRTABLE_BASE_ID")
    airtable_table = os.environ.get("AIRTABLE_TABLE_NAME", "Feedback")
 
    if not airtable_key or not airtable_base:
        # Silently log and return OK — don't expose missing config to client
        logger.warning("Feedback received but AIRTABLE_API_KEY/BASE_ID not configured")
        return {"status": "ok"}
 
    payload = {
        "fields": {
            "Rating":    req.rating,
            "Comment":   req.comment,
            "Timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "Session":   req.session_id[:64],
        }
    }
 
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"https://api.airtable.com/v0/{airtable_base}/{airtable_table}",
                headers={
                    "Authorization": f"Bearer {airtable_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Airtable write failed: {e}")
        # Don't surface Airtable errors to client
        return {"status": "ok"}
 
    return {"status": "ok"}
