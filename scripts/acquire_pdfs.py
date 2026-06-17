"""
acquire_pdfs.py — Agentic PDF acquisition from AF e-Publishing.

Uses Playwright to drive the JS SPA, intercept API calls, extract PDF links
for specified series, and download new publications.

Usage:
  python3 scripts/acquire_pdfs.py                    # all 3-series (31-38)
  python3 scripts/acquire_pdfs.py --series 31,32     # specific series
  python3 scripts/acquire_pdfs.py --series 36        # single series
  python3 scripts/acquire_pdfs.py --dry-run          # list only, no download

Requires: playwright (pip install playwright && playwright install chromium)
"""

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
REPO_ROOT   = SCRIPTS_DIR.parent
RAW_PDFS    = REPO_ROOT / "raw" / "pdfs"
RAW_PDFS.mkdir(parents=True, exist_ok=True)

# All 3-series AFI series numbers
ALL_SERIES = [31, 32, 33, 34, 35, 36, 38]

# e-Publishing base URL
BASE_URL = "https://www.e-publishing.af.mil"

# Known org IDs for 3-series publications
# orgID=10141 = Air Force Departmental (covers most AFIs)
ORG_IDS = [10141]

# ---------------------------------------------------------------------------
# Playwright acquisition
# ---------------------------------------------------------------------------

async def sniff_api_endpoint(page) -> str | None:
    """Intercept XHR calls to find the publications API endpoint."""
    captured = []

    def on_response(response):
        url = response.url
        if any(x in url.lower() for x in ['publication', 'product', 'getpub', 'epub']):
            if 'json' in response.headers.get('content-type', ''):
                captured.append(url)

    page.on("response", on_response)

    await page.goto(
        f"{BASE_URL}/Product-Index/#/?view=org&orgID=10141&catID=1&isForm=false",
        wait_until="networkidle",
        timeout=30000,
    )
    await asyncio.sleep(3)

    return captured[0] if captured else None


async def get_publications_via_api(context, api_url: str, org_id: int) -> list:
    """Fetch publications list from the discovered API endpoint."""
    page = await context.new_page()
    try:
        # Adapt the URL to the org we want
        url = re.sub(r'orgID=\d+', f'orgID={org_id}', api_url)
        resp = await page.goto(url, wait_until="networkidle", timeout=20000)
        if resp and resp.ok:
            text = await page.content()
            # Extract JSON from page content
            m = re.search(r'\[.*\]', text, re.DOTALL)
            if m:
                return json.loads(m.group(0))
    except Exception as e:
        print(f"  API fetch error: {e}")
    finally:
        await page.close()
    return []


async def scrape_series_links(page, series: int) -> list[dict]:
    """
    Navigate to a series page and extract PDF download links.
    Returns list of {pub_number, title, url, filename}
    """
    results = []

    # Navigate to series filter
    url = (
        f"{BASE_URL}/Product-Index/#/?view=org&orgID=10141&catID=1"
        f"&isForm=false&modID=449&tabID=131"
    )
    await page.goto(url, wait_until="networkidle", timeout=30000)
    await asyncio.sleep(2)

    # Try to find and click series filter if available
    # The SPA may have search/filter functionality
    try:
        search = page.locator('input[placeholder*="search"], input[type="search"]').first
        if await search.is_visible(timeout=2000):
            await search.fill(f"AFI {series}-")
            await asyncio.sleep(2)
    except Exception:
        pass

    # Extract all PDF links on the page
    links = await page.eval_on_selector_all(
        'a[href*=".pdf"], a[href*="Product-Index"]',
        "els => els.map(el => ({href: el.href, text: el.textContent.trim()}))"
    )

    for link in links:
        href = link.get('href', '')
        text = link.get('text', '')

        # Only grab PDF links for this series
        if '.pdf' in href.lower():
            m = re.search(r'(afi|afman|afpd|afh|dafi|dafman)\s*(\d+)-(\d+)', text, re.IGNORECASE)
            if m:
                series_num = int(m.group(2))
                if series_num == series:
                    pub_slug = f"{m.group(1).lower()}{m.group(2)}-{m.group(3)}"
                    results.append({
                        'pub_number': f"{m.group(1).upper()} {m.group(2)}-{m.group(3)}",
                        'title': text,
                        'url': href,
                        'filename': f"{pub_slug}.pdf",
                    })

    return results


async def download_pdf(page, url: str, dest: Path) -> bool:
    """Download a PDF from a direct URL."""
    try:
        resp = await page.goto(url, wait_until="networkidle", timeout=30000)
        if resp and resp.ok:
            content = await resp.body()
            if content[:4] == b'%PDF':
                dest.write_bytes(content)
                return True
    except Exception as e:
        print(f"    Download error: {e}")
    return False


async def acquire(series_list: list[int], dry_run: bool = False) -> dict:
    """Main acquisition coroutine."""
    from playwright.async_api import async_playwright

    results = {'downloaded': [], 'skipped': [], 'errors': []}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )

        # First: sniff the API endpoint
        print("Detecting e-Publishing API endpoint...")
        sniff_page = await context.new_page()
        api_url = await sniff_api_endpoint(sniff_page)
        await sniff_page.close()

        if api_url:
            print(f"  API endpoint: {api_url}")
        else:
            print("  Could not detect API — falling back to link scraping")

        # Acquire per series
        for series in series_list:
            print(f"\n[Series {series}-xxx]")
            page = await context.new_page()

            try:
                pubs = await scrape_series_links(page, series)
                print(f"  Found {len(pubs)} publications")

                for pub in pubs:
                    dest = RAW_PDFS / pub['filename']

                    if dest.exists():
                        print(f"  SKIP  {pub['filename']} (already downloaded)")
                        results['skipped'].append(pub['pub_number'])
                        continue

                    if dry_run:
                        print(f"  DRY   {pub['pub_number']}: {pub['url']}")
                        continue

                    print(f"  GET   {pub['filename']} ...", end=" ", flush=True)
                    ok = await download_pdf(page, pub['url'], dest)
                    if ok:
                        print(f"✓ ({dest.stat().st_size // 1024}KB)")
                        results['downloaded'].append(pub['pub_number'])
                    else:
                        print("✗ FAILED")
                        results['errors'].append(pub['pub_number'])

            except Exception as e:
                print(f"  ERROR scraping series {series}: {e}")
                results['errors'].append(f"series-{series}")
            finally:
                await page.close()

        await browser.close()

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Acquire AFI PDFs from e-Publishing")
    parser.add_argument(
        "--series",
        type=str,
        default="all",
        help="Comma-separated series numbers (e.g. 31,32,36) or 'all'",
    )
    parser.add_argument("--dry-run", action="store_true", help="List only, no download")
    args = parser.parse_args()

    # Parse series list
    if args.series.lower() == "all":
        series_list = ALL_SERIES
    else:
        series_list = [int(s.strip()) for s in args.series.split(",")]

    print(f"Target series: {series_list}")
    print(f"Output dir: {RAW_PDFS}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'DOWNLOAD'}")

    try:
        results = asyncio.run(acquire(series_list, dry_run=args.dry_run))
    except ImportError:
        print("\nERROR: playwright not installed.")
        print("Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"Downloaded: {len(results['downloaded'])}")
    print(f"Skipped:    {len(results['skipped'])}")
    print(f"Errors:     {len(results['errors'])}")

    if results['downloaded']:
        print(f"\nNew publications:")
        for p in results['downloaded']:
            print(f"  {p}")

    if results['errors']:
        print(f"\nFailed:")
        for p in results['errors']:
            print(f"  {p}")


if __name__ == "__main__":
    main()
