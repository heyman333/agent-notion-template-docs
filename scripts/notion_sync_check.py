#!/usr/bin/env python3
"""Notion drift watch.

Fetches the reference (public) Notion page two ways and compares the result
against the committed baseline in sync/notion-snapshot.json:

1. Block types — the unauthenticated loadCachedPageChunkV2 API returns the
   page's block tree; new block types Notion ships (and we add to the page)
   show up as new `type` values.
2. Coarse style tokens — a headless render of the page, probing computed
   styles (content width, body colors, callout/code backgrounds). Deliberately
   coarse: colors and widths only, so DOM churn doesn't spam false positives.

Detection is automatic, fixing is human: on drift this exits 1 and writes a
markdown report; CI turns that into a GitHub issue.

Usage:
  notion_sync_check.py snapshot [--out FILE]   # write a fresh snapshot
  notion_sync_check.py check [--report FILE]   # diff fresh vs baseline
"""
import argparse
import datetime
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

SITE = "https://cautious-shovel-8bd.notion.site"
PAGE_ID = "3ccb975b-320f-8012-8e94-c05534b4df9d"
PAGE_URL = f"{SITE}/{PAGE_ID.replace('-', '')}"
ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE = ROOT / "sync" / "notion-snapshot.json"

# Block types the skill's template currently has a rendering for.
# When the reference page grows a type outside this set, that is a coverage gap.
COVERED_TYPES = {
    "page", "text", "header", "sub_header", "sub_sub_header",
    "bulleted_list", "numbered_list", "to_do", "toggle",
    "quote", "callout", "divider", "code",
    "table", "table_row", "column_list", "column",
    "bookmark", "image",
}

STYLE_PROBE_JS = """
() => {
  const cs = (el, prop) => el ? getComputedStyle(el).getPropertyValue(prop) : null;
  const one = (sel) => document.querySelector(sel);
  const uniq = (sel, prop) => [...new Set(
    [...document.querySelectorAll(sel)].map(el => getComputedStyle(el).getPropertyValue(prop))
  )].sort();
  const content = one('.notion-page-content');
  return {
    content_width: content ? Math.round(content.getBoundingClientRect().width) : null,
    body_color: cs(document.body, 'color'),
    body_background: cs(document.body, 'background-color'),
    callout_backgrounds: uniq('.notion-callout-block > div', 'background-color'),
    code_background: uniq('.notion-code-block > div', 'background-color'),
    quote_border_color: uniq('.notion-quote-block blockquote, .notion-quote-block > div', 'border-left-color'),
    table_border_colors: uniq('.notion-table-block td', 'border-color'),
  };
}
"""


def fetch_block_types():
    body = json.dumps({
        "page": {"id": PAGE_ID},
        "limit": 100,
        "cursor": {"stack": []},
        "verticalColumns": False,
    }).encode()
    req = urllib.request.Request(
        f"{SITE}/api/v3/loadCachedPageChunkV2",
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        },
    )
    data = None
    for attempt in range(3):  # transient 429/5xx happen; weekly CI must not cry wolf
        try:
            data = json.load(urllib.request.urlopen(req, timeout=30))
            break
        except urllib.error.HTTPError as exc:
            if attempt == 2 or exc.code not in (429, 500, 502, 503):
                raise
            time.sleep(30 * (attempt + 1))
    types = {}
    for block in data["recordMap"]["block"].values():
        value = block.get("value", {})
        value = value.get("value", value)
        t = value.get("type")
        if t:
            types[t] = types.get(t, 0) + 1
    return dict(sorted(types.items()))


def fetch_styles():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 2200})
        page.emulate_media(color_scheme="light")
        # networkidle never fires on notion.site (live websockets) — wait for the DOM instead
        page.goto(PAGE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector(".notion-page-content", timeout=45000)
        page.wait_for_timeout(2000)  # let late-hydrating blocks settle
        styles = page.evaluate(STYLE_PROBE_JS)
        browser.close()
    return styles


def take_snapshot():
    return {
        "fetched_at": datetime.date.today().isoformat(),
        "page_url": PAGE_URL,
        "block_types": fetch_block_types(),
        "styles": fetch_styles(),
    }


def diff(baseline, fresh):
    """Returns a list of human-readable drift lines. fetched_at is ignored."""
    lines = []
    old_types, new_types = baseline["block_types"], fresh["block_types"]
    for t in sorted(set(new_types) - set(old_types)):
        covered = "already covered by the skill" if t in COVERED_TYPES \
            else "**NOT covered by the skill — template.html needs a block for it**"
        lines.append(f"- New block type on the reference page: `{t}` ({covered})")
    for t in sorted(set(old_types) - set(new_types)):
        lines.append(f"- Block type disappeared from the reference page: `{t}`")

    old_styles, new_styles = baseline["styles"], fresh["styles"]
    for key in sorted(set(old_styles) | set(new_styles)):
        old_v, new_v = old_styles.get(key), new_styles.get(key)
        if old_v != new_v:
            lines.append(f"- Style token `{key}` changed: `{old_v}` → `{new_v}`")
    return lines


def write_report(path, lines, error=None):
    today = datetime.date.today().isoformat()
    out = [f"## Notion drift report — {today}", ""]
    if error:
        out += ["The sync check itself failed (Notion's unofficial API or DOM may have changed):",
                "", f"```\n{error}\n```", "",
                "Fix `scripts/notion_sync_check.py`, then refresh the baseline with:",
                "`python scripts/notion_sync_check.py snapshot --out sync/notion-snapshot.json`"]
    else:
        out += lines + ["",
                        "After updating `skills/notion-doc/template.html` (and the examples), "
                        "refresh the baseline with:",
                        "`python scripts/notion_sync_check.py snapshot --out sync/notion-snapshot.json`"]
    pathlib.Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--out", default=str(BASELINE))
    check = sub.add_parser("check")
    check.add_argument("--report", default="report.md")
    args = parser.parse_args()

    if args.cmd == "snapshot":
        snapshot = take_snapshot()
        out = pathlib.Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"snapshot written to {out}")
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
    print("in sync with Notion — no drift")
    return 0


if __name__ == "__main__":
    sys.exit(main())
