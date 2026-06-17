"""
build_graph.py — Build the AFI knowledge graph from corpus index.

Extracts nodes (publications + directives) and edges (implements, references,
supersedes) from corpus_index.json and outputs graph.json for D3 visualization.

Also produces graph_index.json for the RAG traversal layer.

Usage:
  python3 scripts/build_graph.py

Outputs:
  wiki/javascripts/graph.json     — D3 force graph data
  wiki/javascripts/graph_index.json — adjacency list for RAG traversal
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from datetime import date

REPO_ROOT    = Path(__file__).parent
INDEX_PATH   = REPO_ROOT / "corpus_index.json"
GRAPH_OUT    = REPO_ROOT / "wiki" / "javascripts" / "graph.json"
GRAPH_IDX    = REPO_ROOT / "wiki" / "javascripts" / "graph_index.json"

# Series color mapping (USAF blue palette variants)
SERIES_COLORS = {
    "31": "#C8102E",   # Security Forces — red
    "32": "#4CAF50",   # Civil Engineering — green
    "33": "#FF9800",   # Communications — orange
    "34": "#9C27B0",   # Services — purple
    "35": "#00BCD4",   # Public Affairs — cyan
    "36": "#003F87",   # Personnel — USAF blue
    "38": "#795548",   # Manpower — brown
    "directive": "#A8B2C1",  # External directives — silver
}

# Node type definitions
NODE_TYPES = {
    "AFI":   {"shape": "circle",  "size": 10},
    "DAFI":  {"shape": "circle",  "size": 10},
    "AFMAN": {"shape": "square",  "size": 9},
    "DAFMAN":{"shape": "square",  "size": 9},
    "AFH":   {"shape": "diamond", "size": 8},
    "AFPD":  {"shape": "triangle","size": 9},
    "DAFPD": {"shape": "triangle","size": 9},
    "AFGM":  {"shape": "circle",  "size": 7},
    "DoDI":  {"shape": "star",    "size": 7},
    "DoDD":  {"shape": "star",    "size": 7},
    "HAFMD": {"shape": "star",    "size": 6},
    "OTHER": {"shape": "circle",  "size": 5},
}

STUB_TYPES = {
    "PLACEHOLDER_PHYSICAL", "PLACEHOLDER_RESTRICTED",
    "PLACEHOLDER_OPR", "VISUAL_AID", "UNKNOWN"
}


def get_series(pub_number: str) -> str:
    m = re.search(r"\b(\d{2})-", pub_number)
    return m.group(1) if m else "??"


def get_pub_type(pub_number: str) -> str:
    m = re.match(r"^(DAFI|AFI|AFMAN|DAFMAN|AFH|DAFH|AFPD|DAFPD|AFGM|DAFGM|DoDI|DoDD|HAFMD)", pub_number, re.IGNORECASE)
    return m.group(1).upper() if m else "OTHER"


def get_color(pub_number: str, pub_type: str) -> str:
    if pub_type in ("DoDI", "DoDD", "HAFMD"):
        return SERIES_COLORS["directive"]
    series = get_series(pub_number)
    return SERIES_COLORS.get(series, "#6B7280")


def wiki_url(pub_number: str, meta: dict) -> str:
    """Generate relative wiki URL for a pub."""
    wiki_file = meta.get("wiki_file", "")
    if wiki_file:
        return f"../{wiki_file.replace('.md', '/')}".replace("//", "/")
    return ""


def build_graph(index: dict) -> dict:
    nodes = {}
    edges = []
    edge_set = set()  # deduplicate

    def add_node(pub_id: str, meta: dict = None, is_external: bool = False):
        if pub_id in nodes:
            return
        pub_type = get_pub_type(pub_id)
        series   = get_series(pub_id)
        doc_type = meta.get("doc_type", "POLICY_FULL") if meta else "EXTERNAL"
        is_stub  = doc_type in STUB_TYPES

        nodes[pub_id] = {
            "id":       pub_id,
            "type":     pub_type,
            "series":   series,
            "title":    meta.get("title", pub_id) if meta else pub_id,
            "opr":      meta.get("opr", "") if meta else "",
            "color":    get_color(pub_id, pub_type),
            "size":     NODE_TYPES.get(pub_type, NODE_TYPES["OTHER"])["size"],
            "shape":    NODE_TYPES.get(pub_type, NODE_TYPES["OTHER"])["shape"],
            "url":      wiki_url(pub_id, meta) if meta else "",
            "external": is_external,
            "stub":     is_stub,
            "doc_type": doc_type,
        }

    def add_edge(source: str, target: str, rel_type: str):
        key = (source, target, rel_type)
        if key in edge_set:
            return
        edge_set.add(key)
        edges.append({
            "source": source,
            "target": target,
            "type":   rel_type,
        })

    # --- Pass 1: Add all corpus pubs as nodes ---
    for pub_num, meta in index.items():
        add_node(pub_num, meta)

    # --- Pass 2: Add edges from metadata ---
    for pub_num, meta in index.items():
        # implements edges
        for impl in meta.get("implements", []):
            impl = impl.strip()
            if not impl:
                continue
            if impl not in nodes:
                add_node(impl, is_external=True)
            add_edge(pub_num, impl, "implements")

        # supersedes edges
        for sup in meta.get("supersedes", []):
            # Extract pub number from "AFI 36-2406, 6 August 2024" format
            m = re.match(r"([A-Z]+\s*\d{2}-\d+)", sup.strip(), re.IGNORECASE)
            if m:
                sup_num = m.group(1).strip().upper()
                # Normalize spacing
                sup_num = re.sub(r'\s+', ' ', sup_num)
                if sup_num not in nodes:
                    add_node(sup_num, is_external=True)
                add_edge(pub_num, sup_num, "supersedes")

        # cross-reference edges (from references field -- same series only to avoid noise)
        pub_series = get_series(pub_num)
        for ref in meta.get("references", []):
            ref = ref.strip()
            if not ref or ref == pub_num:
                continue
            ref_series = get_series(ref)
            # Only draw edges to pubs in the corpus or same series (reduces visual noise)
            if ref in nodes or ref_series == pub_series:
                if ref not in nodes:
                    add_node(ref, is_external=True)
                add_edge(pub_num, ref, "references")

    return {
        "nodes":       list(nodes.values()),
        "edges":       edges,
        "generated":   date.today().isoformat(),
        "corpus_size": len(index),
        "series_colors": SERIES_COLORS,
    }


def build_adjacency_index(graph: dict) -> dict:
    """
    Build adjacency list for RAG traversal.
    {pub_id: {implements: [], referenced_by: [], supersedes: [], implements_back: []}}
    """
    adj = defaultdict(lambda: defaultdict(list))

    for edge in graph["edges"]:
        src, tgt, rel = edge["source"], edge["target"], edge["type"]
        adj[src][rel].append(tgt)
        # reverse edges
        reverse = {
            "implements":  "implemented_by",
            "references":  "referenced_by",
            "supersedes":  "superseded_by",
        }
        if rel in reverse:
            adj[tgt][reverse[rel]].append(src)

    return {k: dict(v) for k, v in adj.items()}


def main():
    if not INDEX_PATH.exists():
        print("corpus_index.json not found. Run ingest_pdfs.py first.")
        return

    index = json.loads(INDEX_PATH.read_text())
    print(f"Building graph from {len(index)} publications...")

    graph = build_graph(index)

    n_nodes     = len(graph["nodes"])
    n_edges     = len(graph["edges"])
    n_external  = sum(1 for n in graph["nodes"] if n["external"])
    n_stubs     = sum(1 for n in graph["nodes"] if n.get("stub"))
    n_corpus    = n_nodes - n_external

    print(f"  Corpus nodes:   {n_corpus}")
    print(f"  External nodes: {n_external} (directives + cross-refs)")
    print(f"  Stub nodes:     {n_stubs} (coverage gaps)")
    print(f"  Edges:          {n_edges}")
    print(f"    implements:   {sum(1 for e in graph['edges'] if e['type'] == 'implements')}")
    print(f"    references:   {sum(1 for e in graph['edges'] if e['type'] == 'references')}")
    print(f"    supersedes:   {sum(1 for e in graph['edges'] if e['type'] == 'supersedes')}")

    GRAPH_OUT.write_text(json.dumps(graph, indent=2))
    print(f"\nGraph:     {GRAPH_OUT}")

    adj = build_adjacency_index(graph)
    GRAPH_IDX.write_text(json.dumps(adj, indent=2))
    print(f"Adjacency: {GRAPH_IDX}")


if __name__ == "__main__":
    main()
