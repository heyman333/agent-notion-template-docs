#!/usr/bin/env python3
"""PostToolUse 훅 — HTML 문서를 쓰고 나면 notion-doc 정본을 지켰는지 본다.

두 갈래로 동작한다.

1. 파일에 정본 지문(--callout-blue, --radius, .page)이 있으면 → lint.py 를 돌려
   오류를 그대로 돌려준다. 에이전트가 CSS 를 새로 지었거나 클래스를 지어냈으면
   여기서 잡힌다.
2. 지문이 없는데 혼자 서는 문서형 HTML 이면 → skill 을 안 거쳤다는 뜻이므로
   한 줄 안내만 낸다.

앱·컴포넌트·빌드 산출물은 건드리지 않는다. 어떤 예외가 나도 "{}" 를 내고
0 으로 끝난다(fail-open) — 훅이 작업을 막는 일은 없어야 한다.

계약: stdin JSON(tool_name, tool_input.file_path) → stdout
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

# 문서가 아니라 앱·빌드 산출물이면 쳐다보지 않는다.
SKIP_PARTS = {"node_modules", "dist", "build", ".next", "out", "vendor",
              "coverage", ".venv", "target", "public"}
APP_SIGNALS = (
    'id="root"', "id='root'", 'id="app"', '<script type="module"',
    "{{", "<%", "data-reactroot", "__NEXT_DATA__",
    "</template>", "<slot", "{% ",
)
# 프레임워크 속성 접두사는 태그 안 공백 뒤에 올 때만 인정한다. 그냥 부분 문자열로
# 보면 "padding-left" 가 ng-, "max-width:" 가 th: 로 잡힌다.
APP_ATTR_RE = re.compile(
    r"\s(?:ng-[a-z]|th:[a-z]|v-(?:if|for|else|bind|model|on)\b|x-data\b|asp-[a-z])")


def load_linter():
    spec = importlib.util.spec_from_file_location("notion_doc_lint", LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def looks_like_document(text):
    """혼자 서는 문서형 HTML 인가 — 앱 껍데기·템플릿 조각은 제외."""
    low = text.lower()
    if "<html" not in low and "<!doctype" not in low:
        return False
    if not re.search(r"<h1[ >]", low):
        return False
    if any(sig.lower() in low for sig in APP_SIGNALS):
        return False
    return not APP_ATTR_RE.search(low)


def build_message(path, findings):
    lines = [f"notion-doc 검증 실패 — {path}", ""]
    lines += [f"  {'ERROR' if s == 'error' else 'WARN '} [{c}] {m}"
              for s, c, m in findings]
    lines += [
        "",
        f"{TEMPLATE} 의 <style> 블록은 한 글자도 바꾸지 말고 본문만 고쳐라.",
        f"블록 선택 규칙은 {SKILL} 에 있다.",
        f"다시 확인: python3 {LINT} {path}",
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
            return (f"{path} 는 문서형 HTML 인데 notion-doc skill 이 적용되지 "
                    f"않았다. {SKILL} 을 읽고 {TEMPLATE} 을 복사해서 다시 만들어라 "
                    "— CSS 를 직접 짓지 말 것.")
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
