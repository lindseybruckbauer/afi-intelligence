import re
import json
from pathlib import Path

WIKI_ROOT = Path(__file__).parent / "wiki"
SKIP = {"index", "chat", "log", "graph"}

def extract_links(content):
    return re.findall(r'\[\[([^\]]+)\]\]', content)

nodes = {}
edges = []

for md_file in WIKI_ROOT.rglob("*.md"):
    name = md_file.stem
    if name in SKIP:
        continue
    rel = str(md_file.relative_to(WIKI_ROOT))
    
    if "entities" in rel:
        node_type = "entity"
    elif "concepts" in rel:
        node_type = "concept"
    elif "sources" in rel:
        node_type = "source"
    else:
        node_type = "other"
    
    nodes[name] = {"id": name, "type": node_type, "path": rel}
    
    content = md_file.read_text()
    links = extract_links(content)
    for link in links:
        if link != name:
            edges.append({"source": name, "target": link})

valid_edges = [
    e for e in edges 
    if e["source"] in nodes and e["target"] in nodes
]

graph = {
    "nodes": list(nodes.values()),
    "edges": valid_edges
}

out = Path(__file__).parent / "wiki" / "javascripts" / "graph.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(graph, indent=2))
print(f"Graph: {len(nodes)} nodes, {len(valid_edges)} edges → {out}")
