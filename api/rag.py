"""
rag.py — ChromaDB query layer for the AFI chat assistant.

Import this from api/main.py.
The collection name and CHROMA_DIR must match ingest_pdfs.py.

v2: adds graph-augmented retrieval via graph_index.json.
When a user query mentions specific pub numbers, graph traversal
expands context to include related pubs (1 hop: implements/references).
"""

import json
import re
from pathlib import Path

_CHROMA_DIR       = Path(__file__).parent.parent / "chroma_db"
_GRAPH_INDEX_PATH = Path(__file__).parent.parent / "wiki" / "javascripts" / "graph_index.json"

_client      = None
_collection  = None
_graph_index = None   # cached on first load


# ---------------------------------------------------------------------------
# ChromaDB init
# ---------------------------------------------------------------------------

def _col():
    global _client, _collection
    if _collection is None:
        try:
            import chromadb
        except ImportError:
            raise RuntimeError("chromadb not installed: pip install chromadb")
        _client     = chromadb.PersistentClient(path=str(_CHROMA_DIR))
        _collection = _client.get_or_create_collection(
            name="afi_corpus",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ---------------------------------------------------------------------------
# Graph index helpers
# ---------------------------------------------------------------------------

def _load_graph_index() -> dict:
    """Load and cache graph_index.json. Returns {} if file missing."""
    global _graph_index
    if _graph_index is None:
        if _GRAPH_INDEX_PATH.exists():
            try:
                _graph_index = json.loads(_GRAPH_INDEX_PATH.read_text(encoding="utf-8"))
            except Exception:
                _graph_index = {}
        else:
            _graph_index = {}
    return _graph_index


# Matches standard AF pub number formats in user queries.
# Used to identify graph traversal starting points -- never passed raw to DB.
_PUB_RE = re.compile(
    r'\b(DAFI|AFI|AFMAN|AFPD|AFH|DAFMAN|DAFH|AFPAM|AFGM|DAFGM|AFJI|DAFPD)\s+\d{2}[-\s]\d+\b',
    re.IGNORECASE,
)


def _extract_pub_refs(text: str) -> list[str]:
    """Extract and normalize pub numbers mentioned in query text."""
    found = set()
    for m in _PUB_RE.finditer(text):
        # Normalize: uppercase, collapse internal whitespace
        normalized = re.sub(r'\s+', ' ', m.group(0).strip().upper())
        found.add(normalized)
    return list(found)


def _graph_expand(mentioned: list[str], graph_index: dict) -> set[str]:
    """
    1-hop expansion: given a list of mentioned pub numbers,
    return the set of all directly related pubs (implements + references).
    """
    related = set(mentioned)  # include the mentioned pubs themselves
    for pub in mentioned:
        node = graph_index.get(pub, {})
        for neighbor in node.get("implements", []) + node.get("references", []):
            related.add(neighbor)
    return related


# ---------------------------------------------------------------------------
# Semantic query (unchanged from v1)
# ---------------------------------------------------------------------------

def query(question: str, n_results: int = 6) -> list:
    """
    Semantic search over the AFI corpus.
    Returns list of dicts: {text, pub_number, title, section_number, section_title, distance}
    Lower distance = more relevant (cosine space, 0..2).
    """
    col   = _col()
    count = col.count()
    if count == 0:
        return []

    results = col.query(
        query_texts=[question],
        n_results=min(n_results, count),
        include=["documents", "metadatas", "distances"],
    )

    return _parse_results(results)


# ---------------------------------------------------------------------------
# Graph-augmented query (new in v2)
# ---------------------------------------------------------------------------

def graph_query(question: str, n_results: int = 6) -> tuple[list, list]:
    """
    Graph-augmented retrieval.

    1. Extract pub numbers mentioned in the question.
    2. Expand 1 hop via graph_index.json (implements + references).
    3. Fetch semantically-relevant chunks for those pubs from ChromaDB.

    Returns:
        (chunks, expanded_pubs)
        chunks        — list of chunk dicts (same format as query())
        expanded_pubs — list of pub numbers traversal found (for logging/annotation)

    Returns ([], []) if no pub numbers detected in query.
    """
    graph_index = _load_graph_index()
    if not graph_index:
        return [], []

    mentioned = _extract_pub_refs(question)
    if not mentioned:
        return [], []

    related = _graph_expand(mentioned, graph_index)
    if not related:
        return [], []

    col   = _col()
    count = col.count()
    if count == 0:
        return [], []

    # Filter to pubs that actually have chunks in ChromaDB.
    # Avoids wasted queries for external pubs (DoDI, DoDD) not in corpus.
    try:
        results = col.query(
            query_texts=[question],
            n_results=min(n_results, count),
            where={"pub_number": {"$in": list(related)}},
            include=["documents", "metadatas", "distances"],
        )
        chunks = _parse_results(results)
    except Exception:
        # ChromaDB $in filter can fail if no matching docs; treat as empty
        chunks = []

    expanded = sorted(related - set(mentioned))  # neighbors only, for annotation
    return chunks, expanded


# ---------------------------------------------------------------------------
# Merge + deduplicate
# ---------------------------------------------------------------------------

def merge_chunks(semantic: list, graph: list, max_chunks: int = 10) -> list:
    """
    Merge semantic and graph-retrieved chunks, deduplicate by text content,
    prefer lower distance on collision, cap at max_chunks.
    """
    seen   = {}   # text[:120] → chunk
    merged = []

    for chunk in semantic + graph:
        key = chunk["text"][:120]
        if key not in seen:
            seen[key] = chunk
            merged.append(chunk)
        else:
            # Keep the version with lower (better) distance
            if chunk["distance"] < seen[key]["distance"]:
                seen[key]["distance"] = chunk["distance"]

    # Sort by relevance, cap
    merged.sort(key=lambda c: c["distance"])
    return merged[:max_chunks]


# ---------------------------------------------------------------------------
# Formatting (unchanged from v1)
# ---------------------------------------------------------------------------

def format_context(chunks: list) -> str:
    """Format retrieved chunks for injection into the system prompt."""
    if not chunks:
        return "(No relevant AFI content found in corpus for this query.)"

    parts = []
    for c in chunks:
        source = c["pub_number"]
        if c["section_number"]:
            source += f" \u00a7{c['section_number']}"
        if c["section_title"]:
            source += f" \u2014 {c['section_title']}"
        parts.append(f"[{source}]\n{c['text']}")

    return "\n\n---\n\n".join(parts)


def corpus_stats() -> dict:
    """Return basic stats about the loaded corpus."""
    try:
        col = _col()
        graph_index = _load_graph_index()
        return {
            "total_chunks":   col.count(),
            "graph_nodes":    len(graph_index),
            "status":         "ok",
        }
    except Exception as e:
        return {"total_chunks": 0, "graph_nodes": 0, "status": str(e)}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_results(results: dict) -> list:
    """Parse raw ChromaDB query results into chunk dicts."""
    chunks = []
    for text, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        if dist > 0.9:   # filter noise
            continue
        chunks.append({
            "text":           text,
            "pub_number":     meta.get("pub_number", ""),
            "title":          meta.get("title", ""),
            "section_number": meta.get("section_number", ""),
            "section_title":  meta.get("section_title", ""),
            "distance":       round(dist, 4),
        })
    return chunks
