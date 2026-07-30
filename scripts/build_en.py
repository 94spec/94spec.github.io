#!/usr/bin/env python3
"""Generate the English page from the Russian one.

The site carries both languages in data-ru/data-en attributes and swaps them in
the browser. That is enough for a visitor and not enough for anything else: a
crawler indexes only what is in the markup, so the English half of the site does
not exist for search, and there is no URL to send to an English-speaking reader.

This produces /en/index.html from index.html with the English strings promoted
into the markup. One source of truth stays index.html; CI regenerates and diffs,
so the two can never drift.

Usage: python scripts/build_en.py [--check]
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "index.html"
TARGET = ROOT / "en" / "index.html"

NODE = re.compile(r'<(?P<tag>[a-z0-9]+)(?P<attrs>[^>]*?)\sdata-ru="(?P<ru>[^"]*)"'
                  r'\s+data-en="(?P<en>[^"]*)"(?P<rest>[^>]*)>(?P<inner>.*?)</(?P=tag)>',
                  re.S)

HEAD_SWAPS = [
    ('<html lang="ru">', '<html lang="en">'),
    ('<link rel="canonical" href="https://94spec.github.io/">',
     '<link rel="canonical" href="https://94spec.github.io/en/">'),
    ('<meta property="og:url" content="https://94spec.github.io/">',
     '<meta property="og:url" content="https://94spec.github.io/en/">'),
    ('<meta property="og:locale" content="ru_RU">',
     '<meta property="og:locale" content="en_US">'),
    ('<meta property="og:locale:alternate" content="en_US">',
     '<meta property="og:locale:alternate" content="ru_RU">'),
    ("<title>Дмитрий Пром — резюме", "<title>Dmitry Prom — CV"),
]

EN_TITLE = "Dmitry Prom — AI Engineer &amp; Data Analyst (LLM-based analytics)"
EN_DESCRIPTION = ("I build production LLM systems for commercial processes and do the analysis "
                  "on the data they produce: quality control across customer communications, "
                  "voice AI, enterprise RAG, evaluation and model economics.")


def promote(source: str) -> str:
    """Replace each bilingual node's visible text with its English string."""

    def swap(match: re.Match) -> str:
        english = match.group("en")
        # The attribute is HTML-escaped; the inner text must not be double-escaped.
        inner = html.unescape(english)
        return (f'<{match.group("tag")}{match.group("attrs")} data-ru="{match.group("ru")}"'
                f' data-en="{match.group("en")}"{match.group("rest")}>{inner}'
                f'</{match.group("tag")}>')

    # Innermost nodes first, so a swapped parent does not erase a nested child.
    previous = None
    text = source
    while previous != text:
        previous = text
        text = NODE.sub(swap, text)
    return text


def build() -> str:
    source = SOURCE.read_text(encoding="utf-8")
    text = promote(source)

    for old, new in HEAD_SWAPS:
        text = text.replace(old, new)

    text = re.sub(r"<title>[^<]*</title>", f"<title>{EN_TITLE}</title>", text, count=1)
    text = re.sub(r'<meta name="description" content="[^"]*">',
                  f'<meta name="description" content="{EN_DESCRIPTION}">', text, count=1)
    text = re.sub(r'<meta property="og:title" content="[^"]*">',
                  f'<meta property="og:title" content="{EN_TITLE}">', text, count=1)
    text = re.sub(r'<meta name="twitter:title" content="[^"]*">',
                  f'<meta name="twitter:title" content="{EN_TITLE}">', text, count=1)

    # One URL per language, so the switch is a link on both pages — here it
    # points back to Russian, and English is the page you are on.
    switch_ru = ('      <span class="langlink current" aria-current="page">ru</span>\n'
                 '      <a class="langlink" href="/en/" hreflang="en">en</a>')
    switch_en = ('      <a class="langlink" href="/" hreflang="ru">ru</a>\n'
                 '      <span class="langlink current" aria-current="page">en</span>')
    if switch_ru not in text:
        raise SystemExit("the language switch markup changed — update build_en.py")
    text = text.replace(switch_ru, switch_en)

    return text


def main() -> int:
    generated = build()
    check = "--check" in sys.argv

    if check:
        if not TARGET.exists():
            print(f"{TARGET} does not exist — run scripts/build_en.py")
            return 1
        if TARGET.read_text(encoding="utf-8") != generated:
            print(f"{TARGET} is out of date — run scripts/build_en.py")
            return 1
        print(f"{TARGET.relative_to(ROOT)} is up to date")
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(generated, encoding="utf-8", newline="\n")
    print(f"wrote {TARGET.relative_to(ROOT)} ({len(generated.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
