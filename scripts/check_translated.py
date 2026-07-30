#!/usr/bin/env python3
"""Fail if a page meant to be English still renders Russian.

The bilingual source keeps both languages in attributes, and the English page is
generated from it. A string added without its `data-en` twin, or a value written
as plain text in the markup, silently stays Russian on /en/ — invisible in review
because the page looks fine in a browser set to Russian.

Usage: python scripts/check_translated.py en/index.html
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def rendered_text(source: str) -> str:
    body = re.sub(r"(?s)<(script|style).*?</\1>", "", source)
    body = re.sub(r"(?s)<!--.*?-->", "", body)
    body = re.sub(r'data-(?:ru|en)="[^"]*"', "", body)  # attributes are not rendered
    return re.sub(r"<[^>]+>", " ", body)


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "en/index.html")
    if not target.exists():
        print(f"not found: {target}")
        return 1

    visible = rendered_text(target.read_text(encoding="utf-8"))
    leftovers = []
    for match in CYRILLIC.finditer(visible):
        start = max(0, match.start() - 60)
        snippet = " ".join(visible[start:match.end() + 40].split())
        leftovers.append(snippet)
        if len(leftovers) >= 5:
            break

    if leftovers:
        print(f"{target}: Russian text is still rendered on the English page")
        for snippet in leftovers:
            print(f"  … {snippet} …")
        print("\nAdd the missing data-en twin, then run scripts/build_en.py")
        return 1

    words = len(re.findall(r"[A-Za-z]{2,}", visible))
    print(f"{target}: fully translated ({words} English words rendered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
