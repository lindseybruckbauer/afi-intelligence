"""
build_publications.py — Generate wiki/publications.md from corpus_index.json.

Organized by series, with status indicators for full pubs, stubs, and sparse docs.
Run after ingest_pdfs.py.

Can also be imported and called from build_index.py.
"""

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INDEX_PATH = REPO_ROOT / "corpus_index.json"
OUTPUT_PATH = REPO_ROOT / "wiki" / "publications.md"

STUB_TYPES = {
    "PLACEHOLDER_PHYSICAL", "PLACEHOLDER_RESTRICTED",
    "PLACEHOLDER_OPR", "VISUAL_AID", "UNKNOWN"
}

SERIES_LABELS = {
    "31": "Security Forces",
    "32": "Civil Engineering",
    "33": "Communications & Information",
    "34": "Services",
    "35": "Public Affairs",
    "36": "Personnel",
    "37": "Air Force Publishing",
    "38": "Manpower & Organization",
}

STATUS_BADGES = {
    "POLICY_FULL":             "✅ Full",
    "POLICY_SPARSE":           "⚠️ Sparse",
    "PLACEHOLDER_PHYSICAL":    "📦 Physical only",
    "PLACEHOLDER_RESTRICTED":  "🔒 Restricted",
    "PLACEHOLDER_OPR":         "📋 Contact OPR",
    "VISUAL_AID":              "🖼️ Visual aid",
    "UNKNOWN":                 "❓ Unknown",
}


def get_series(pub_number: str) -> str:
    import re
    # AFGM 2026-36-2033 → series 36 (skip the year component)
    m = re.match(r'^(?:AFGM|DAFGM)\s+\d{4}-(\d{2})-', pub_number, re.IGNORECASE)
    if m:
        return m.group(1)
    # Standard: AFI 36-2406, DAFI 31-118 → first XX- pattern after the prefix
    m = re.search(r'(?:^|\s)(\d{2})-', pub_number)
    if m:
        return m.group(1)
    return "??"


def build_publications_page(index: dict) -> str:
    # Group by series
    by_series = defaultdict(list)
    for pub_num, meta in index.items():
        series = get_series(pub_num)
        by_series[series].append((pub_num, meta))

    # Sort each series by pub number
    for series in by_series:
        by_series[series].sort(key=lambda x: x[0])

    total = len(index)
    full_count = sum(1 for m in index.values() if m.get("doc_type", "POLICY_FULL") == "POLICY_FULL")
    stub_count = sum(1 for m in index.values() if m.get("status") == "stub")
    sparse_count = sum(1 for m in index.values() if m.get("doc_type") == "POLICY_SPARSE")

    lines = [
        "# Publications",
        "",
        f"*{total} publications in corpus · {full_count} fully analyzed · "
        f"{sparse_count} sparse · {stub_count} coverage gaps · "
        f"last updated {date.today().strftime('%d %B %Y')}*",
        "",
        "<div class='usaf-disclaimer'>",
        "All source documents are publicly available via "
        "<a href='https://www.e-publishing.af.mil'>AF e-Publishing</a>. "
        "Coverage gaps (🔒📦📋) indicate publications that exist in the catalog "
        "but are not digitally accessible for analysis.",
        "</div>",
        "",
    ]

    for series in sorted(by_series.keys()):
        pubs = by_series[series]
        if series == "??":
            label = "Coverage Gaps — Unknown Series"
        else:
            label = SERIES_LABELS.get(series, f"{series}-series")
        series_full = sum(
            1 for _, m in pubs
            if m.get("doc_type", "POLICY_FULL") in ("POLICY_FULL", "POLICY_SPARSE")
        )
        series_stubs = sum(1 for _, m in pubs if m.get("status") == "stub")

        lines += [
            f"## {series}-Series — {label}",
            "",
            f"*{len(pubs)} publications · {series_full} analyzed · {series_stubs} gaps*",
            "",
            "| Publication | Title | OPR | Status |",
            "|-------------|-------|-----|--------|",
        ]

        for pub_num, meta in pubs:
            doc_type = meta.get("doc_type", "POLICY_FULL")
            status = meta.get("status", "ok")
            wiki_file = meta.get("wiki_file", "")
            title = meta.get("title", "")

            # Clean up title for display
            if title.startswith("[") and "]" in title:
                title = ""  # stub titles are just doc_type markers
            # Clean up common bad title patterns from extraction
            if any(title.startswith(x) for x in [
                "Incorporating Change", "Department of the Air Force Guidance Memorandum to",
                "MCO ", "www.e-publishing", "[www", "Unknown Title",
            ]):
                title = ""
            title = title[:55] + "…" if len(title) > 55 else title

            badge = STATUS_BADGES.get(doc_type, "✅ Full")
            opr = meta.get("opr", "")

            # Link to wiki page if it exists
            if wiki_file:
                page_link = wiki_file  # MkDocs converts .md links to correct HTML paths
                pub_cell = f"[{pub_num}]({page_link})"
            else:
                pub_cell = pub_num

            lines.append(f"| {pub_cell} | {title} | {opr} | {badge} |")

        lines.append("")

    lines += [
        "---",
        "",
        "## Legend",
        "",
        "| Status | Meaning |",
        "|--------|---------|",
        "| ✅ Full | Fully analyzed — wiki page + semantic search available |",
        "| ⚠️ Sparse | Analyzed with limited content (short pub or thin text) |",
        "| 🔒 Restricted | Restricted access — content not publicly available |",
        "| 📦 Physical only | Physical product only — no digital text available |",
        "| 📋 Contact OPR | Stocked and issued — request copy from OPR |",
        "| 🖼️ Visual aid | Image-based document — text extraction insufficient |",
        "",
        "---",
        "",
        "*To add more publications: download PDFs to `raw/pdfs/` and run "
        "`python3 scripts/run_pipeline.py --commit`*",
    ]

    return "\n".join(lines)


def main():
    if not INDEX_PATH.exists():
        print("corpus_index.json not found. Run ingest_pdfs.py first.")
        return

    index = json.loads(INDEX_PATH.read_text())
    content = build_publications_page(index)
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"Written: {OUTPUT_PATH}")
    print(f"  {len(index)} publications across "
          f"{len(set(p.split()[1].split('-')[0] if len(p.split()) > 1 else '??' for p in index))} series")


if __name__ == "__main__":
    main()
