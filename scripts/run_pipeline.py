"""
run_pipeline.py — Agentic pipeline orchestrator.

Full sequence:
  1. Ingest PDFs (extract + classify + synthesize + embed)
  2. Analyze corpus (gaps, overlaps, authority matrix)
  3. Build home page index
  4. Build publications page
  5. Build knowledge graph
  6. Optionally commit + push

Usage:
  python3 scripts/run_pipeline.py                    # new PDFs only
  python3 scripts/run_pipeline.py --force            # re-ingest everything
  python3 scripts/run_pipeline.py --commit           # also git commit + push
  python3 scripts/run_pipeline.py --force --commit   # full refresh + deploy
  python3 scripts/run_pipeline.py --dry-run          # extract only, no API calls
  python3 scripts/run_pipeline.py --no-analysis      # skip analysis (faster iteration)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
REPO_ROOT   = SCRIPTS_DIR.parent


def run(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, check=check, cwd=REPO_ROOT)


def count_pdfs() -> int:
    return len(list((REPO_ROOT / "raw" / "pdfs").glob("*.pdf")))


def count_wiki_pages() -> int:
    wiki = REPO_ROOT / "wiki"
    prefixes = ("afi", "afh", "afgm", "dafi", "afman", "afpd", "afji", "afva", "dafman")
    return len([f for f in wiki.glob("*.md") if f.stem.lower().startswith(prefixes)])


def git_status() -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="AFI Intelligence pipeline orchestrator")
    parser.add_argument("--force",       action="store_true", help="Re-ingest all PDFs")
    parser.add_argument("--commit",      action="store_true", help="Git commit + push after pipeline")
    parser.add_argument("--dry-run",     action="store_true", help="Extract only, no API calls")
    parser.add_argument("--no-analysis", action="store_true", help="Skip analysis step (faster)")
    parser.add_argument("--message",     type=str, default="", help="Custom commit message")
    args = parser.parse_args()

    # Validate environment
    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    print("=" * 60)
    print("AFI INTELLIGENCE PIPELINE")
    print("=" * 60)
    print(f"PDFs in raw/pdfs/:   {count_pdfs()}")
    print(f"Existing wiki pages: {count_wiki_pages()}")
    print(f"Mode:  {'FORCE RE-INGEST' if args.force else 'NEW ONLY'}")
    print(f"Commit: {'YES' if args.commit else 'NO'}")
    print()

    # Step 1: Ingest
    ingest_cmd = [sys.executable, "scripts/ingest_pdfs.py"]
    if args.force:   ingest_cmd.append("--force")
    if args.dry_run: ingest_cmd.append("--dry-run")
    run(ingest_cmd)

    if args.dry_run:
        print("\nDry run complete — skipping analysis, graph, and commit.")
        return

    # Step 2: Analysis
    if not args.no_analysis and not os.environ.get("SKIP_ANALYSIS"):
        run([sys.executable, "scripts/analyze_corpus.py"])
    else:
        print("\nSkipping analysis (--no-analysis or SKIP_ANALYSIS=1)")

    # Step 3: Build index (home page)
    run([sys.executable, "scripts/build_index.py"])

    # Step 4: Build publications page
    run([sys.executable, "scripts/build_publications.py"])

    # Step 5: Build knowledge graph
    run([sys.executable, "build_graph.py"])

    print("\n" + "=" * 60)
    print(f"Pipeline complete. Wiki pages: {count_wiki_pages()}")
    print("=" * 60)

    # Step 6: Commit + push
    if args.commit and not os.environ.get("SKIP_COMMIT"):
        changes = git_status()
        if not changes:
            print("\nNo changes to commit.")
            return

        print(f"\nChanged files:\n{changes}\n")
        msg = args.message or f"Pipeline: {count_wiki_pages()} publications ingested and analyzed"

        run(["git", "add",
             "wiki/", "chroma_db/", "corpus_index.json",
             "scripts/", "build_graph.py"])
        run(["git", "commit", "-m", msg])
        run(["git", "push"])
        print(f"\nPushed. Deploy in ~60 seconds.")
        print(f"Site: https://lindseybruckbauer.github.io/afi-intelligence/")
    elif args.commit:
        print("\nSKIP_COMMIT=1 set — skipping commit.")
    else:
        print("\nRun with --commit to push changes.")
        changes = git_status()
        if changes:
            print(f"Pending:\n{changes}")


if __name__ == "__main__":
    main()
