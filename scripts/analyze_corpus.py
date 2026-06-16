"""
analyze_corpus.py — Run policy analysis across the full AFI corpus.

Produces three wiki pages:
  wiki/ANALYSIS_overlaps.md     — overlapping/conflicting authorities
  wiki/ANALYSIS_gaps.md         — policy gaps and thin coverage
  wiki/ANALYSIS_authority_matrix.md — who can do what, across all pubs

Usage:
  python scripts/analyze_corpus.py
  python scripts/analyze_corpus.py --only gaps     # single analysis
  python scripts/analyze_corpus.py --only overlaps
  python scripts/analyze_corpus.py --only matrix
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Missing dep: pip install anthropic")
    sys.exit(1)

SCRIPTS_DIR = Path(__file__).parent
REPO_ROOT   = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from extract_pdf import extract

WIKI_DIR   = REPO_ROOT / "wiki"
RAW_PDFS   = REPO_ROOT / "raw" / "pdfs"
INDEX_PATH = REPO_ROOT / "corpus_index.json"

client = anthropic.Anthropic()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_index() -> dict:
    if not INDEX_PATH.exists():
        print("corpus_index.json not found. Run ingest_pdfs.py first.")
        sys.exit(1)
    return json.loads(INDEX_PATH.read_text())


def load_wiki(meta: dict) -> str:
    """Load the synthesized wiki page for a publication."""
    path = WIKI_DIR / meta.get("wiki_file", f"{Path(meta['file']).stem}.md")
    if path.exists():
        return path.read_text(encoding="utf-8")[:2000]  # cap per-pub context
    return f"(wiki not found for {meta['pub_number']})"


def _ask(prompt: str, max_tokens: int = 3500) -> str:
    resp = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


# ---------------------------------------------------------------------------
# Analysis 1: Overlaps & Conflicts
# ---------------------------------------------------------------------------

def analyze_overlaps(index: dict) -> str:
    print("  Building overlap context...")

    pub_blobs = []
    for pub_num in sorted(index):
        meta = index[pub_num]
        wiki = load_wiki(meta)
        pub_blobs.append(
            f"### {pub_num}: {meta['title']}\n"
            f"OPR: {meta['opr']} | Implements: {', '.join(meta.get('implements', []))}\n\n"
            f"{wiki}\n"
        )

    corpus_block = "\n---\n".join(pub_blobs)

    prompt = f"""You are a DoD policy analyst reviewing a corpus of Air Force Instructions (AFIs).

Below are synthesized wiki pages for each AFI in the corpus.

Your task: identify OVERLAPS, CONFLICTS, and REDUNDANCIES across these publications.

Definitions:
- OVERLAP: Two or more AFIs assign authority or responsibility for the same function/activity
  to different offices, potentially creating confusion about who is actually in charge.
- CONFLICT: Two AFIs give contradictory guidance — one says SHALL, another says MAY for the same action.
- REDUNDANCY: Substantial duplication of content/requirements between pubs where one could defer to the other.

For each finding:
- Name the specific pubs involved (e.g., AFI 36-2406 vs AFI 36-2502)
- Describe the overlap/conflict concisely (2-3 sentences)
- Assign a severity: HIGH (operational impact), MEDIUM (administrative friction), LOW (cosmetic)
- Suggest resolution (which pub should own it, or that a supplement is needed)

Format as markdown:

## Summary
Total findings: X | HIGH: X | MEDIUM: X | LOW: X

## Findings

### Finding 1 — [Short title] [HIGH/MEDIUM/LOW]
**Pubs:** AFI X vs AFI Y
**Issue:** ...
**Resolution:** ...

[repeat for each finding]

## Notes
Any corpus-level observations (e.g., "The 36-series has heavy overlap in civilian personnel authority").

---
CORPUS WIKI PAGES:
{corpus_block}"""

    return _ask(prompt, max_tokens=4000)


# ---------------------------------------------------------------------------
# Analysis 2: Gaps
# ---------------------------------------------------------------------------

def analyze_gaps(index: dict) -> str:
    print("  Building gap context...")

    # Cross-reference: which DoDIs are referenced but potentially under-implemented
    dodi_to_pubs = defaultdict(list)
    for pub_num, meta in index.items():
        for ref in meta.get("implements", []) + meta.get("references", []):
            if "DoDI" in ref.upper() or "DoDD" in ref.upper():
                dodi_to_pubs[ref].append(pub_num)

    series_present = sorted(set(
        pub.split()[1].split("-")[0]
        for pub in index
        if len(pub.split()) > 1 and "-" in pub.split()[1]
    ))

    titles_json = json.dumps(
        {k: {"title": v["title"], "opr": v["opr"]} for k, v in index.items()},
        indent=2
    )

    references_json = json.dumps(dict(dodi_to_pubs), indent=2)

    prompt = f"""You are a DoD policy analyst auditing a set of Air Force Instructions for coverage gaps.

CORPUS OVERVIEW:
- Series present: {', '.join(f'AFI {s}-xxx' for s in series_present)}
- Publications in corpus: {len(index)}
- Note: This may be a SUBSET of all active AFIs in these series.

PUBLICATION TITLES & OPRs:
{titles_json}

DoDI/DoDD REFERENCES FOUND IN CORPUS:
{references_json}

Your task: identify GAPS — areas where policy coverage is missing, thin, or unclear.

Gap types to look for:
1. MISSING AUTHORITY: A common military function within these series (personnel management,
   security forces, civil engineering, etc.) where no AFI clearly assigns authority.
2. THIN DODI COVERAGE: A DoDI that is referenced in an AFI header ("Implements") but
   whose requirements may not be fully addressed in the document body.
3. SERIES GAPS: Topic areas that belong in a given series but appear unaddressed
   by any pub in this corpus (accounting for the possibility of pubs not in this corpus).
4. EXPIRED/SUPERSEDED REFERENCES: Signs that pubs reference outdated higher-level directives.

Format as markdown:

## Summary
[Brief characterization of the corpus's coverage overall]

## Gap Findings

### Gap 1 — [Short title]
**Type:** Missing Authority / Thin DoDI Coverage / Series Gap / Expired Reference
**Affected Series/Pubs:** ...
**Description:** ...
**Recommended Action:** ...

[repeat]

## DoDI Coverage Assessment
[Table or bullets assessing each DoDI reference: well-covered / thin / unclear]

## Notes
[Caveats, corpus limitations, recommended follow-on analysis]"""

    return _ask(prompt, max_tokens=4000)


# ---------------------------------------------------------------------------
# Analysis 3: Authority Matrix
# ---------------------------------------------------------------------------

def analyze_authority_matrix(index: dict) -> str:
    print("  Extracting authority statements from PDFs...")

    all_statements = []
    for pub_num, meta in sorted(index.items()):
        pdf_path = RAW_PDFS / meta["file"]
        if not pdf_path.exists():
            print(f"    WARN: PDF not found for {pub_num}, skipping authority extraction")
            continue
        try:
            doc = extract(pdf_path)
            for stmt in doc.authority_statements[:20]:
                all_statements.append({"pub": pub_num, "statement": stmt})
        except Exception as e:
            print(f"    WARN: could not re-extract {pub_num}: {e}")

    if not all_statements:
        return "No authority statements could be extracted. Check that PDFs are in raw/pdfs/."

    stmts_json = json.dumps(all_statements, indent=2)

    prompt = f"""You are a DoD policy analyst building an authority matrix from Air Force Instructions.

Below are sentences extracted from AFIs that grant, delegate, restrict, or describe authority.

Your task: organize these into a structured authority matrix.

PART 1 — AUTHORITY MATRIX TABLE
Produce a markdown table:
| Role / Office | Action / Function | Conditions or Limits | Source AFI | Section |
|---------------|-------------------|----------------------|------------|---------|

Rules:
- Each row = one discrete authority grant
- "Role/Office" = specific role (e.g., Wing Commander, MAJCOM/CC, SAF/MR, Installation Commander)
- "Action/Function" = what they're authorized to do (be specific)
- "Conditions/Limits" = any stated restrictions, thresholds, or delegation conditions
- "Source AFI" = publication number
- Include only statements that are specific enough to be actionable

PART 2 — CONFLICTING OR AMBIGUOUS AUTHORITIES
Identify cases where:
- Two different roles are both assigned the same authority in different pubs
- A statement is vague about WHICH commander level has the authority
- Delegation chains are unclear

Format as bullets:
- [Issue description] — See [AFI X] vs [AFI Y]

PART 3 — AUTHORITY GAPS
Functions that appear in the corpus but where no clear authority is assigned.

---
EXTRACTED AUTHORITY STATEMENTS:
{stmts_json}"""

    return _ask(prompt, max_tokens=5000)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def write_output(filename: str, header: str, content: str):
    path = WIKI_DIR / filename
    path.write_text(
        f"{header}\n\n*Auto-generated by analyze_corpus.py — do not edit manually.*\n\n{content}",
        encoding="utf-8"
    )
    print(f"  → {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only",
        choices=["overlaps", "gaps", "matrix"],
        help="Run only one analysis",
    )
    args = parser.parse_args()

    index = load_index()
    print(f"Loaded {len(index)} publications from corpus index.\n")

    run_all = args.only is None

    if run_all or args.only == "overlaps":
        print("Running: overlap analysis...")
        result = analyze_overlaps(index)
        write_output(
            "ANALYSIS_overlaps.md",
            "# Policy Overlaps & Conflicts",
            result,
        )

    if run_all or args.only == "gaps":
        print("\nRunning: gap analysis...")
        result = analyze_gaps(index)
        write_output(
            "ANALYSIS_gaps.md",
            "# Policy Gaps",
            result,
        )

    if run_all or args.only == "matrix":
        print("\nRunning: authority matrix...")
        result = analyze_authority_matrix(index)
        write_output(
            "ANALYSIS_authority_matrix.md",
            "# Authority Matrix",
            result,
        )

    print("\nAll analysis complete. Commit wiki/ and push to deploy.")


if __name__ == "__main__":
    main()
