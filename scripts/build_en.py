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

    # Root-absolute asset paths keep working from /en/; the language buttons
    # become links between the two URLs, because on this page the swap is done.
    text = text.replace(
        '      <button type="button" id="lang-ru" aria-pressed="true">ru</button>\n'
        '      <button type="button" id="lang-en" aria-pressed="false">en</button>',
        '      <a class="langlink" href="/" hreflang="ru">ru</a>\n'
        '      <span class="langlink current" aria-current="page">en</span>')
    text = text.replace(
        ".langbox button{font:inherit;",
        ".langbox .langlink{display:inline-flex;align-items:center;text-decoration:none;"
        "font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;padding:6px 10px;"
        "color:var(--muted)}\n"
        ".langbox .langlink.current{background:var(--accent);color:var(--bg);font-weight:700}\n"
        ".langbox button{font:inherit;")

    # The language script has nothing to do here: this page is already English.
    text = re.sub(r"  var nodes = document\.querySelectorAll.*?if \(saved === \"en\"\) apply\(\"en\"\);",
                  "  // This page ships English in the markup; only the menu needs behaviour.",
                  text, flags=re.S)
    text = text.replace('  ruBtn.addEventListener("click", function () { apply("ru"); });\n', "")
    text = text.replace('  enBtn.addEventListener("click", function () { apply("en"); });\n', "")
    text = re.sub(r"  var ruBtn = .*?\n  var enBtn = .*?\n", "", text)

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
