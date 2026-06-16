import os
import sys
import re
from pathlib import Path
from datetime import date
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

def read_file(path):
    try:
        return Path(path).read_text()
    except:
        return ""

def write_file(path, content):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content)
    print(f"  wrote: {path}")

def ingest(source_path):
    if not Path(source_path).exists():
        print(f"File not found: {source_path}")
        sys.exit(1)

    print(f"Ingesting: {source_path}")

    schema    = read_file("AGENTS.md")
    index     = read_file("wiki/index.md")
    log       = read_file("wiki/log.md")
    source    = Path(source_path).read_text()

    prompt = f"""You are maintaining a team knowledge wiki.

SCHEMA (follow exactly):
{schema}

CURRENT INDEX:
{index}

SOURCE TO INGEST ({source_path}):
{source}

Today's date: {date.today()}

Instructions:
- Process this source according to the ingest workflow in the schema
- Return ONLY file blocks in this exact format, nothing else:

<file path="wiki/sources/...">
content here
</file>

<file path="wiki/index.md">
full updated index here
</file>

<file path="wiki/log.md">
full updated log here
</file>

Include any entity or concept pages created or updated.
"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    output = response.content[0].text
    files  = re.findall(r'<file path="([^"]+)">(.*?)</file>', output, re.DOTALL)

    if not files:
        print("No files returned. Raw output:")
        print(output)
        sys.exit(1)

    for path, content in files:
        write_file(path, content.strip())

    print(f"\nDone. {len(files)} files written.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ingest.py raw/your-file.md")
        sys.exit(1)
    ingest(sys.argv[1])
