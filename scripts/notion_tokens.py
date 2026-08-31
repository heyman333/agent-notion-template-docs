#!/usr/bin/env python3
"""Notion palette extractor — the accurate way to "따오다" Notion's CSS.

Notion ships its entire design-token table as CSS custom properties inside
its own stylesheets, scoped per theme:

    :root, .notion-light-theme { --c-texPri:#2c2c2b; ... }   (~740 tokens)
    .notion-dark-theme         { --c-texPri:#f0efed; ... }   (~590 tokens)

So instead of sampling pixels off a rendered page (lossy, selector-fragile),
this script reads the token table verbatim from the source of truth:

1. GET the reference notion.site page HTML (plain urllib, no browser).
2. Find the hash-versioned stylesheet hrefs (/_assets/*.css).
3. Parse every rule scoped to .notion-light-theme / .notion-dark-theme and
   collect all `--*` declarations.

The result (sync/notion-tokens.json) is the committed palette canon. What it
does NOT know is which token each block type actually paints with — that
mapping (plus geometry) comes from scripts/notion_style_probe.py.

Usage:
  notion_tokens.py snapshot [--out FILE]   # write a fresh token table
  notion_tokens.py check [--report FILE]   # diff fresh vs committed baseline
"""
import argparse
import datetime
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

REFERENCE_URL = "https://thomasfrank.notion.site/8b40147600284c60b6f708e38f16ee68"
ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE = ROOT / "sync" / "notion-tokens.json"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")

LIGHT_SEL = ".notion-light-theme"
DARK_SEL = ".notion-dark-theme"


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):  # same retry posture as notion_sync_check.py
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if attempt == 2 or exc.code not in (429, 500, 502, 503):
                raise
            time.sleep(30 * (attempt + 1))


def stylesheet_urls(page_html, base_url):
    """Hash-versioned stylesheet URLs referenced by the page (print.css excluded)."""
    origin = re.match(r"https?://[^/]+", base_url).group(0)
    hrefs = re.findall(r'<link[^>]+href="([^"]+\.css[^"]*)"[^>]*>', page_html)
    urls = []
    for href in hrefs:
        if "print" in href:
            continue
        urls.append(href if href.startswith("http") else origin + href)
    return urls


def parse_theme_tokens(css_text):
    """All --* declarations from rules scoped to the light/dark theme classes.

    Token-table rules are flat (no nesting), so a non-greedy brace match is
    safe; a selector list like `:root,.notion-light-theme` counts as light.
    """
    light, dark = {}, {}
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css_text):
        selector, body = m.group(1), m.group(2)
        if LIGHT_SEL not in selector and DARK_SEL not in selector:
            continue
        decls = dict(re.findall(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;]+)", body))
        if not decls:
            continue
        if LIGHT_SEL in selector:
            light.update(decls)
        if DARK_SEL in selector:
            dark.update(decls)
    return light, dark


def take_snapshot():
    page_html = http_get(REFERENCE_URL)
    light, dark = {}, {}
    sources = []
    for url in stylesheet_urls(page_html, REFERENCE_URL):
        l, d = parse_theme_tokens(http_get(url))
        if l or d:
            sources.append(url)
        light.update(l)
        dark.update(d)
    if len(light) < 100 or len(dark) < 100:  # Notion changed its bundling — go blind loudly
        raise RuntimeError(
            f"token table suspiciously small (light={len(light)}, dark={len(dark)}) — "
            "Notion may have moved its theme tokens out of these stylesheets")
    return {
        "fetched_at": datetime.date.today().isoformat(),
        "reference_url": REFERENCE_URL,
        "source_stylesheets": sources,
        "tokens": {
            "light": dict(sorted(light.items())),
            "dark": dict(sorted(dark.items())),
        },
    }


def diff(baseline, fresh):
    """Human-readable drift lines; fetched_at and stylesheet hashes are ignored."""
    lines = []
    for theme in ("light", "dark"):
        old = baseline["tokens"][theme]
        new = fresh["tokens"][theme]
        for k in sorted(set(new) - set(old)):
            lines.append(f"- [{theme}] New token `{k}` = `{new[k]}`")
        for k in sorted(set(old) - set(new)):
            lines.append(f"- [{theme}] Token removed: `{k}` (was `{old[k]}`)")
        for k in sorted(set(old) & set(new)):
            if old[k] != new[k]:
                lines.append(f"- [{theme}] `{k}` changed: `{old[k]}` → `{new[k]}`")
    return lines


def write_report(path, lines, error=None):
    today = datetime.date.today().isoformat()
    out = [f"## Notion token drift report — {today}", ""]
    if error:
        out += ["Token extraction itself failed (Notion's stylesheet layout may have "
                "changed, or the reference page moved):",
                "", f"```\n{error}\n```"]
    else:
        out += lines + [
            "",
            "If a token the skill maps (see sync/notion-style-map.json) changed, update "
            "`skills/notion-doc/template.html` and the examples, then refresh baselines:",
            "`python scripts/notion_tokens.py snapshot --out sync/notion-tokens.json`",
        ]
    pathlib.Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--out", default=str(BASELINE))
    check = sub.add_parser("check")
    check.add_argument("--report", default="token-report.md")
    args = parser.parse_args()

    if args.cmd == "snapshot":
        snapshot = take_snapshot()
        out = pathlib.Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        n = snapshot["tokens"]
        print(f"{len(n['light'])} light / {len(n['dark'])} dark tokens → {out}")
        return 0

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    try:
        fresh = take_snapshot()
    except Exception as exc:  # fetch failure is drift too: the watcher went blind
        write_report(args.report, [], error=repr(exc))
        print(f"FETCH FAILED: {exc!r}", file=sys.stderr)
        return 1
    lines = diff(baseline, fresh)
    if lines:
        write_report(args.report, lines)
        print("\n".join(lines), file=sys.stderr)
        return 1
    print("token table in sync with Notion — no drift")
    return 0


if __name__ == "__main__":
    sys.exit(main())
