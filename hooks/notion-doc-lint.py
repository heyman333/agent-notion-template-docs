#!/usr/bin/env python3
"""PostToolUse hook — after an HTML document is written, check the notion-doc canon.

Two modes of operation:

1. If the file carries the canon fingerprint (--callout-blue, --radius, .page)
   → run lint.py and pass its errors through. Catches the agent writing new
   CSS or inventing classes.
2. If the fingerprint is missing but the file is a standalone document-shaped
   HTML → the skill was skipped, so emit a one-line reminder.

Apps, components, and build artifacts are left alone. On any exception it
prints "{}" and exits 0 (fail-open) — the hook must never block work.

Contract: stdin JSON (tool_name, tool_input.file_path) → stdout
          hookSpecificOutput.additionalContext
"""
import importlib.util
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINT = ROOT / "skills" / "notion-doc" / "lint.py"
SKILL = ROOT / "skills" / "notion-doc" / "SKILL.md"
TEMPLATE = ROOT / "skills" / "notion-doc" / "template.html"

FINGERPRINT = ("--callout-blue", "--radius", ".page")

# Don't even look at apps or build artifacts — documents only.
SKIP_PARTS = {"node_modules", "dist", "build", ".next", "out", "vendor",
              "coverage", ".venv", "target", "public"}
APP_SIGNALS = (
    'id="root"', "id='root'", 'id="app"', '<script type="module"',
    "{{", "<%", "data-reactroot", "__NEXT_DATA__",
    "</template>", "<slot", "{% ",
)
# Framework attribute prefixes only count after whitespace inside a tag.
# As plain substrings, "padding-left" matches ng- and "max-width:" matches th:.
APP_ATTR_RE = re.compile(
    r"\s(?:ng-[a-z]|th:[a-z]|v-(?:if|for|else|bind|model|on)\b|x-data\b|asp-[a-z])")


def load_linter():
    spec = importlib.util.spec_from_file_location("notion_doc_lint", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def looks_like_document(text):
    """Standalone document-shaped HTML — app shells and template fragments excluded."""
    low = text.lower()
    if "<html" not in low and "<!doctype" not in low:
        return False
    if not re.search(r"<h1[ >]", low):
        return False
    if any(sig.lower() in low for sig in APP_SIGNALS):
        return False
    return not APP_ATTR_RE.search(low)


def build_message(path, findings):
    lines = [f"notion-doc check failed — {path}", ""]
    lines += [f"  {'ERROR' if s == 'error' else 'WARN '} [{c}] {m}"
              for s, c, m in findings]
    lines += [
        "",
        f"Do not change a single character of the <style> block in {TEMPLATE} — fix only the body.",
        f"Block selection rules are in {SKILL}.",
        f"Re-check with: python3 {LINT} {path}",
    ]
    return "\n".join(lines)


def run(data):
    if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return None
    raw = (data.get("tool_input") or {}).get("file_path")
    if not raw:
        return None
    path = pathlib.Path(raw)
    if path.suffix.lower() not in (".html", ".htm"):
        return None
    if SKIP_PARTS & set(path.parts):
        return None
    if not path.is_file():
        return None

    text = path.read_text(encoding="utf-8", errors="replace")

    if not all(m in text for m in FINGERPRINT):
        if looks_like_document(text):
            return (f"{path} is a document-shaped HTML file but the notion-doc "
                    f"skill was not applied. Read {SKILL} and rebuild it by "
                    f"copying {TEMPLATE} — do not write your own CSS.")
        return None

    linter = load_linter()
    findings = linter.check(path, linter.canon_style())
    if not any(s == "error" for s, _, _ in findings):
        return None
    return build_message(path, findings)


def main():
    output = "{}"
    try:
        message = run(json.load(sys.stdin))
        if message:
            output = json.dumps({"hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": message,
            }}, ensure_ascii=False)
    except Exception:
        output = "{}"
    try:
        print(output)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
