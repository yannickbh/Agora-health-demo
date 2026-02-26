"""
ingest.py — Knowledge base ingestion script

Usage:
    python ingest.py <use_case>
    python ingest.py hospital
    python ingest.py --all

For each source defined in config.json, fetches the content and combines
into a single knowledge_base.md file ready for the agent.

Supported source types:
    local   — reads a local file (relative to the use case folder)
    url     — fetches content from a public URL and strips HTML tags
"""

import sys
import json
import pathlib
import urllib.request
import html
import re


USE_CASES_DIR = pathlib.Path(__file__).parent / "backend" / "data" / "use_cases"


def strip_html(raw: str) -> str:
    """Remove HTML tags and decode entities."""
    no_tags = re.sub(r"<[^>]+>", " ", raw)
    decoded = html.unescape(no_tags)
    cleaned = re.sub(r"[ \t]+", " ", decoded)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def fetch_local(source: dict, use_case_dir: pathlib.Path) -> str:
    path = use_case_dir / source["path"]
    if not path.exists():
        raise FileNotFoundError(f"Local source not found: {path}")
    print(f"  [local] {path}")
    return path.read_text(encoding="utf-8")


def fetch_url(source: dict) -> str:
    url = source["url"]
    print(f"  [url]   {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return strip_html(raw)


def ingest(use_case: str):
    use_case_dir = USE_CASES_DIR / use_case
    config_path = use_case_dir / "config.json"

    if not config_path.exists():
        print(f"ERROR: Use case '{use_case}' not found at {use_case_dir}")
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    sources = config.get("sources", [])

    if not sources:
        print(f"WARNING: No sources defined in {config_path}")
        return

    print(f"\nIngesting use case: {use_case} ({len(sources)} source(s))")

    sections = []
    for source in sources:
        source_type = source.get("type")
        try:
            if source_type == "local":
                content = fetch_local(source, use_case_dir)
            elif source_type == "url":
                content = fetch_url(source)
            else:
                print(f"  [skip]  Unknown source type: {source_type}")
                continue
            sections.append(content.strip())
        except Exception as e:
            print(f"  [ERROR] Failed to fetch source {source}: {e}")

    if not sections:
        print("ERROR: No content was fetched. knowledge_base.md not updated.")
        sys.exit(1)

    knowledge_base = "\n\n---\n\n".join(sections)
    output_path = use_case_dir / "knowledge_base.md"
    output_path.write_text(knowledge_base, encoding="utf-8")

    print(f"\n  Saved: {output_path}")
    print(f"  Size:  {len(knowledge_base):,} characters\n")


def main():
    args = sys.argv[1:]

    if not args:
        print("Usage: python ingest.py <use_case>")
        print("       python ingest.py --all")
        sys.exit(1)

    if args[0] == "--all":
        use_cases = [d.name for d in USE_CASES_DIR.iterdir() if d.is_dir()]
        if not use_cases:
            print("No use cases found.")
            sys.exit(1)
        for uc in use_cases:
            ingest(uc)
    else:
        ingest(args[0])


if __name__ == "__main__":
    main()
