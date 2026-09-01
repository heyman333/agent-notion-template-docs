#!/usr/bin/env python3
"""notion-doc linter — checks that a generated HTML document kept the style canon.

There is one core check: the document's <style> block must be **byte-identical**
to template.html in this directory. If the agent wrote new CSS, changed a color,
or added a shadow, it gets caught here. The remaining checks cover the body —
inline styles, classes the template doesn't define, code blocks without
highlighting.

No dependencies (standard library only). Runs as-is under any agent.

    python3 lint.py doc.html [more.html ...]
    python3 lint.py --json doc.html      # machine-readable

Exit code: 1 if there is at least one error, 0 if clean or warnings only.
"""
import argparse
import difflib
import json
import pathlib
import re
import sys

CANON = pathlib.Path(__file__).resolve().parent / "template.html"

# Fingerprint that identifies the canon. Without it, the document never
# started from the template in the first place.
FINGERPRINT = ("--callout-blue", "--radius", ".page")

# Classes Prism adds at runtime and language-tag classes are fine without CSS.
CLASS_OK_PREFIX = ("language-", "token")

DIFF_PREVIEW = 6


def _between(text, open_tag, close_tag):
    try:
        start = text.index(open_tag) + len(open_tag)
        return text[start:text.index(close_tag, start)]
    except ValueError:
        return None


def _strip_comments(html):
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def canon_style():
    return _between(CANON.read_text(encoding="utf-8"), "<style>", "</style>")


def check(path, canon):
    """Returns a list of (severity, code, message)."""
    out = []
    text = path.read_text(encoding="utf-8", errors="replace")
    style = _between(text, "<style>", "</style>")
    body = _between(text, "<body>", "</body>")
    if body is None:  # template.html is a skeleton without <body>
        body = text.split("</style>", 1)[-1]

    if style is None or not all(m in style for m in FINGERPRINT):
        out.append(("error", "no-template",
                    "Document does not start from template.html. Copy the style canon"))
        return out  # without the canon the remaining checks are meaningless

    if style != canon:
        d = [l for l in difflib.unified_diff(
                canon.splitlines(), style.splitlines(),
                "template.html", str(path), lineterm="", n=0)
             if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
        preview = "; ".join(l.strip() for l in d[:DIFF_PREVIEW])
        more = f" (+{len(d) - DIFF_PREVIEW} more lines)" if len(d) > DIFF_PREVIEW else ""
        out.append(("error", "css-drift",
                    f"CSS differs from the canon ({len(d)} lines). "
                    f"Do not write new CSS — {preview}{more}"))

    body_clean = _strip_comments(body)

    if 'style="' in body_clean or "style='" in body_clean:
        out.append(("error", "inline-style",
                    "Body contains inline style attributes. Use template classes only"))

    colors = re.findall(r"#[0-9A-Fa-f]{3,8}\b|\brgba?\(", body_clean)
    if colors:
        out.append(("error", "raw-color",
                    f"Body contains raw colors ({', '.join(sorted(set(colors))[:4])}). "
                    "Colors only via t-* classes and callout classes"))

    defined = set(re.findall(r"\.([A-Za-z][\w-]*)", style))
    used = set()
    for attr in re.findall(r'class="([^"]*)"', body_clean):
        used.update(attr.split())
    unknown = sorted(c for c in used - defined
                     if not c.startswith(CLASS_OK_PREFIX))
    if unknown:
        out.append(("error", "unknown-class",
                    f"Classes not in the template: {', '.join(unknown[:6])}. "
                    "Do not invent classes — pick from the block dictionary"))

    if "language-" in body_clean and "prism" not in text.lower():
        out.append(("error", "missing-prism",
                    "language-* code blocks present but the Prism scripts are missing"))

    plain_code = re.findall(r"<pre>\s*<code(?![^>]*class=)", body_clean)
    if plain_code:
        out.append(("warn", "code-no-language",
                    f"{len(plain_code)} code block(s) without a language — "
                    'add class="language-<lang>" to get highlighting'))

    missing = [name for name, pat in (
        ("page icon", r'class="page-icon"'),
        ("title (h1)", r"<h1[ >]"),
        ("meta line", r'class="meta"'),
        ("divider", r"<hr\b"),
    ) if not re.search(pat, body_clean)]
    if missing:
        out.append(("warn", "header-shape",
                    f"Header area is missing: {', '.join(missing)} (SKILL.md section 1)"))

    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="notion-doc style canon linter")
    ap.add_argument("files", nargs="+", type=pathlib.Path)
    ap.add_argument("--json", action="store_true", help="machine-readable JSON output")
    args = ap.parse_args(argv)

    canon = canon_style()
    if canon is None:
        print(f"Cannot read the canon: {CANON}", file=sys.stderr)
        return 2

    report, failed = {}, False
    for f in args.files:
        if not f.is_file():
            report[str(f)] = [("error", "not-found", "File not found")]
            failed = True
            continue
        found = check(f, canon)
        report[str(f)] = found
        failed |= any(sev == "error" for sev, _, _ in found)

    if args.json:
        print(json.dumps(
            {p: [{"severity": s, "code": c, "message": m} for s, c, m in v]
             for p, v in report.items()}, ensure_ascii=False))
    else:
        for p, found in report.items():
            if not found:
                print(f"✓ {p}")
                continue
            print(f"✗ {p}" if any(s == "error" for s, _, _ in found) else f"! {p}")
            for sev, code, msg in found:
                print(f"  {'ERROR' if sev == 'error' else 'WARN '} [{code}] {msg}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
