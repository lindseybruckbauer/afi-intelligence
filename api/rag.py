"""
rag.py — ChromaDB query layer for the AFI chat assistant.

Import this from api/main.py.
The collection name and CHROMA_DIR must match ingest_pdfs.py.
"""

from pathlib import Path

_CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

_client     = None
_collection = None


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


def query(question: str, n_results: int = 6) -> list:
    """
    Semantic search over the AFI corpus.
    Returns list of dicts: {text, pub_number, title, section_number, section_title, distance}
    Lower distance = more relevant (cosine space, 0..2).
    """
    col = _col()
    count = col.count()
    if count == 0:
        return []

    results = col.query(
        query_texts=[question],
        n_results=min(n_results, count),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for text, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # Filter noise: cosine distance > 0.9 is usually irrelevant
        if dist > 0.9:
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


def format_context(chunks: list) -> str:
    """Format retrieved chunks for injection into the system prompt."""
    if not chunks:
        return "(No relevant AFI content found in corpus for this query.)"

    parts = []
    for c in chunks:
        source = c["pub_number"]
        if c["section_number"]:
            source += f" §{c['section_number']}"
        if c["section_title"]:
            source += f" — {c['section_title']}"
        parts.append(f"[{source}]\n{c['text']}")

    return "\n\n---\n\n".join(parts)


def corpus_stats() -> dict:
    """Return basic stats about the loaded corpus."""
    try:
        col = _col()
        return {"total_chunks": col.count(), "status": "ok"}
    except Exception as e:
        return {"total_chunks": 0, "status": str(e)}
