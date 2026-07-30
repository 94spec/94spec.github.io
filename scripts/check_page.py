#!/usr/bin/env python3
"""Static checks for the portfolio page.

Verifies the things that actually break the site for a visitor or a crawler:
markup balance, required metadata in <head>, working in-page anchors,
referenced local assets, and the absence of placeholder or fake-data tokens.

Usage: python scripts/check_page.py [index.html]
Exit code 1 if any check fails.
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

REQUIRED_HEAD = (
    '<html lang="ru"',
    '<meta name="description"',
    '<link rel="canonical"',
    '<link rel="icon"',
    'property="og:title"',
    'property="og:description"',
    'property="og:image"',
    'property="og:url"',
    'name="twitter:card"',
    'application/ld+json',
)

# Literal tokens that must never reach production: template leftovers,
# unfinished content, randomised "live" values, bundler scaffolding.
FORBIDDEN = ("{{", "TODO:", "FIXME", "Math.random", "lorem ipsum", "__bundler")

# Shapes of confidential material, described generically so that this guard
# does not itself publish the names it is meant to keep out: internal hosts,
# issue keys, record identifiers and plain-HTTP intranet links.
CONFIDENTIAL_SHAPES = (
    (r"https?://[\w.-]+\.(?:pro|local|internal|lan|corp)\b", "internal hostname"),
    (r"http://(?!localhost|127\.0\.0\.1)[\w.-]+", "plain-HTTP link to a non-public host"),
    (r"\b[A-Z]{3,6}-\d{3,6}\b", "issue tracker key"),
    (r"(?<!\d)\d{8}(?!\d)", "eight-digit record identifier"),
    (r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "raw uuid"),
)


class Markup(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.errors: list[str] = []
        self.ids: set[str] = set()
        self.anchors: set[str] = set()
        self.local_assets: set[str] = set()
        self.translatable = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        if attr.get("id"):
            self.ids.add(attr["id"])
        if "data-ru" in attr and "data-en" in attr:
            self.translatable += 1
        if tag == "img" and not attr.get("alt"):
            self.errors.append(f"line {self.getpos()[0]}: <img> without alt")
        for key in ("href", "src"):
            value = attr.get(key, "")
            if value.startswith("#") and len(value) > 1:
                self.anchors.add(value[1:])
            elif value.startswith("/") and not value.startswith("//"):
                self.local_assets.add(value.lstrip("/"))
        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_ELEMENTS:
            return
        if not self.stack:
            self.errors.append(f"line {self.getpos()[0]}: stray </{tag}>")
            return
        open_tag, line = self.stack[-1]
        if open_tag == tag:
            self.stack.pop()
            return
        self.errors.append(
            f"line {self.getpos()[0]}: </{tag}> closes <{open_tag}> opened on line {line}")
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return


def site_root(path: Path) -> Path:
    """Root-absolute hrefs (/fonts/...) resolve against the site root, which is
    the directory holding .nojekyll -- not the directory of a nested page."""
    for candidate in [path.parent, *path.parent.parents]:
        if (candidate / ".nojekyll").exists():
            return candidate
    return path.parent


def check(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    root = site_root(path)
    parser = Markup()
    parser.feed(source)

    problems = list(parser.errors)
    problems += [f"unclosed <{tag}> opened on line {line}" for tag, line in parser.stack]
    problems += [f"missing in <head>: {tag}" for tag in REQUIRED_HEAD if tag not in source]
    problems += [f"forbidden token {token!r} ({source.count(token)}x)"
                 for token in FORBIDDEN if token in source]
    for shape, description in CONFIDENTIAL_SHAPES:
        found = re.findall(shape, source)
        if found:
            problems.append(f"{description} in page: {found[0]!r} ({len(found)}x)")
    problems += [f"anchor #{anchor} has no target" for anchor in sorted(parser.anchors - parser.ids)]
    problems += [f"missing local asset: {asset}"
                 for asset in sorted(parser.local_assets) if not (root / asset).exists()]

    for family in re.findall(r'src:url\("(/fonts/[^"]+)"\)', source.replace(" ", "")):
        if not (root / family.lstrip("/")).exists():
            problems.append(f"missing font file: {family}")

    size_kb = len(source.encode("utf-8")) / 1024
    if size_kb > 250:
        problems.append(f"page is {size_kb:.0f} KB — over the 250 KB budget")

    print(f"{path.name}: {size_kb:.0f} KB, {source.count(chr(10)) + 1} lines, "
          f"{parser.translatable} translatable nodes, {len(parser.ids)} ids")
    return problems


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
    if not target.exists():
        print(f"not found: {target}")
        return 1
    problems = check(target)
    if problems:
        print("\nFAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("OK: markup balanced, metadata present, anchors and assets resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
