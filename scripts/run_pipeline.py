"""
run_pipeline.py — Agentic pipeline orchestrator.

Wraps the full sequence:
  1. Ingest new PDFs (or --force all)
  2. Re-run analysis
  3. Rebuild index
  4. Optionally commit + push

Usage:
  python3 scripts/run_pipeline.py                    # new PDFs only
  python3 scripts/run_pipeline.py --force            # re-ingest everything
  python3 scripts/run_pipeline.py --commit           # also git commit + push
  python3 scripts/run_pipeline.py --force --commit   # full refresh + deploy
  python3 scripts/run_pipeline.py --dry-run          # extract only, no API calls

Environment:
  ANTHROPIC_API_KEY  — required
  SKIP_ANALYSIS      — set to 1 to skip analysis step (faster iteration)
  SKIP_COMMIT        — set to 1 to skip commit even if --commit passed
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
    return len([f for f in (REPO_ROOT / "wiki").glob("afi*.md")] +
               [f for f in (REPO_ROOT / "wiki").glob("afh*.md")] +
               [f for f in (REPO_ROOT / "wiki").glob("afgm*.md")] +
               [f for f in (REPO_ROOT / "wiki").glob("dafi*.md")])


def git_status() -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="AFI Intelligence pipeline orchestrator")
    parser.add_argument("--force",    action="store_true", help="Re-ingest all PDFs")
    parser.add_argument("--commit",   action="store_true", help="Git commit + push after pipeline")
    parser.add_argument("--dry-run",  action="store_true", help="Extract only, no API calls")
    parser.add_argument("--no-analysis", action="store_true", help="Skip analysis step")
    parser.add_argument("--message",  type=str, default="", help="Custom commit message")
    args = parser.parse_args()

    # Validate environment
    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    print("=" * 60)
    print("AFI INTELLIGENCE PIPELINE")
    print("=" * 60)
    print(f"PDFs in raw/pdfs/:  {count_pdfs()}")
    print(f"Existing wiki pages: {count_wiki_pages()}")
    print(f"Mode: {'FORCE RE-INGEST' if args.force else 'NEW ONLY'}")
    print(f"Commit: {'YES' if args.commit else 'NO'}")
    print()

    # Step 1: Ingest
    ingest_cmd = [sys.executable, "scripts/ingest_pdfs.py"]
    if args.force:
        ingest_cmd.append("--force")
    if args.dry_run:
        ingest_cmd.append("--dry-run")
    run(ingest_cmd)

    if args.dry_run:
        print("\nDry run complete — skipping analysis, index, and commit.")
        return

    # Step 2: Analysis
    if not args.no_analysis and not os.environ.get("SKIP_ANALYSIS"):
        run([sys.executable, "scripts/analyze_corpus.py"])
    else:
        print("\nSkipping analysis (--no-analysis or SKIP_ANALYSIS=1)")

    # Step 3: Rebuild index
    run([sys.executable, "scripts/build_index.py"])

    print("\n" + "=" * 60)
    print(f"Pipeline complete. Wiki pages: {count_wiki_pages()}")
    print("=" * 60)

    # Step 4: Commit + push
    if args.commit and not os.environ.get("SKIP_COMMIT"):
        changes = git_status()
        if not changes:
            print("\nNo changes to commit.")
            return

        print(f"\nChanged files:\n{changes}\n")

        pub_count = count_wiki_pages()
        msg = args.message or f"Pipeline: {pub_count} publications ingested and analyzed"

        run(["git", "add", "wiki/", "chroma_db/", "corpus_index.json"])
        run(["git", "commit", "-m", msg])
        run(["git", "push"])
        print(f"\nPushed. Deploy will complete in ~60 seconds.")
        print(f"Site: https://lindseybruckbauer.github.io/afi-intelligence/")
    elif args.commit:
        print("\nSKIP_COMMIT=1 set — skipping commit.")
    else:
        print("\nRun with --commit to push changes.")
        print("Pending changes:")
        print(git_status() or "  (none)")


if __name__ == "__main__":
    main()
