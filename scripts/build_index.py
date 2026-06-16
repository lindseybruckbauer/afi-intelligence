"""
build_index.py — Regenerate wiki/index.md from corpus_index.json.

Run after any ingest or analysis pass:
  python3 scripts/build_index.py

Reads:  corpus_index.json
Writes: wiki/index.md  (replaces existing home page)
"""

import json
from pathlib import Path
from datetime import date

REPO_ROOT   = Path(__file__).parent.parent
INDEX_PATH  = REPO_ROOT / "corpus_index.json"
WIKI_DIR    = REPO_ROOT / "wiki"
OUTPUT_PATH = WIKI_DIR / "index.md"

def main():
    if not INDEX_PATH.exists():
        print("corpus_index.json not found — run ingest_pdfs.py first")
        return

    index = json.loads(INDEX_PATH.read_text())

    # Sort pubs: AFGM/AFH first by type, then by pub number
    def sort_key(item):
        pub_num = item[0]
        prefix = pub_num.split()[0]
        order = {"AFI": 0, "DAFI": 0, "AFMAN": 1, "DAFMAN": 1,
                 "AFPD": 2, "AFH": 3, "AFGM": 4, "DAFGM": 4}
        return (order.get(prefix, 9), pub_num)

    sorted_pubs = sorted(index.items(), key=sort_key)

    # Find analysis pages
    analysis_files = sorted(WIKI_DIR.glob("ANALYSIS_*.md"))

    analysis_label = {
        "ANALYSIS_overlaps":        ("Policy Overlaps & Conflicts",  "Where two or more publications assign conflicting or overlapping authority"),
        "ANALYSIS_gaps":            ("Policy Gaps",                  "Missing coverage, thin DoDI implementation, and unaddressed policy domains"),
        "ANALYSIS_authority_matrix":("Authority Matrix",             "Who has authority to do what, with citations to specific sections"),
    }

    lines = [
        "# AFI Policy Intelligence — 36-Series Corpus",
        "",
        f"*{len(index)} publications ingested · last updated {date.today().strftime('%d %B %Y')}*",
        "",
        "---",
        "",
        "## Analysis",
        "",
        "Cross-publication analysis generated from the full corpus.",
        "",
    ]

    for f in analysis_files:
        key   = f.stem
        label, desc = analysis_label.get(key, (f.stem.replace("ANALYSIS_", "").replace("_", " ").title(), ""))
        lines.append(f"- **[{label}]({f.name})** — {desc}")

    lines += [
        "",
        "---",
        "",
        "## Publications",
        "",
        "Individual wiki pages synthesized from source PDFs.",
        "",
        "| Publication | Title | OPR | Effective |",
        "|-------------|-------|-----|-----------|",
    ]

    for pub_num, meta in sorted_pubs:
        title    = meta.get("title", "Unknown")
        opr      = meta.get("opr", "Unknown")
        date_str = meta.get("effective_date", "")
        wiki_file = meta.get("wiki_file", f"{Path(meta['file']).stem}.md")
        lines.append(f"| [{pub_num}]({wiki_file}) | {title} | {opr} | {date_str} |")

    lines += [
        "",
        "---",
        "",
        "## About This Tool",
        "",
        "Built on the [Karpathy LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). "
        "Source PDFs are ingested, synthesized into wiki pages via Claude, "
        "and indexed in a local vector store for semantic search.",
        "",
        "Use the **Chat** tab to query across the full corpus in natural language.",
        "",
    ]

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written: {OUTPUT_PATH}")
    print(f"  {len(index)} publications")
    print(f"  {len(analysis_files)} analysis pages")


if __name__ == "__main__":
    main()
