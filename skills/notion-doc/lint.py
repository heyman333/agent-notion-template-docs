#!/usr/bin/env python3
"""notion-doc 검증기 — 생성된 HTML 문서가 스타일 정본을 지켰는지 본다.

핵심 검사는 하나다: 문서의 <style> 블록이 같은 디렉토리의 template.html 과
**한 글자도 다르지 않아야 한다**. 에이전트가 CSS 를 새로 지었거나, 색을 하나
바꿨거나, 그림자를 얹었으면 여기서 걸린다. 나머지 검사는 본문 쪽이다 —
인라인 스타일, 템플릿에 없는 클래스, 하이라이트 빠진 코드 블록.

의존성 없음(표준 라이브러리만). 어떤 에이전트에서든 그냥 실행하면 된다.

    python3 lint.py doc.html [more.html ...]
    python3 lint.py --json doc.html      # 기계용

종료 코드: 오류가 하나라도 있으면 1, 경고만 있거나 깨끗하면 0.
"""
import argparse
import difflib
import json
import pathlib
import re
import sys

CANON = pathlib.Path(__file__).resolve().parent / "template.html"

# 정본이 맞는지 알아보는 지문. 이게 없으면 애초에 템플릿에서 시작하지 않은 문서다.
FINGERPRINT = ("--callout-blue", "--radius", ".page")

# Prism 이 런타임에 붙이는 클래스와 언어 지정 클래스는 CSS 에 없어도 정상이다.
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
    """[(severity, code, message)] 목록을 돌려준다."""
    out = []
    text = path.read_text(encoding="utf-8", errors="replace")
    style = _between(text, "<style>", "</style>")
    body = _between(text, "<body>", "</body>")
    if body is None:  # template.html 은 <body> 없는 스켈레톤이다
        body = text.split("</style>", 1)[-1]

    if style is None or not all(m in style for m in FINGERPRINT):
        out.append(("error", "no-template",
                    "template.html 에서 시작하지 않았다. 스타일 정본을 복사해 쓸 것"))
        return out  # 정본이 아예 없으면 나머지 검사는 의미가 없다

    if style != canon:
        d = [l for l in difflib.unified_diff(
                canon.splitlines(), style.splitlines(),
                "template.html", str(path), lineterm="", n=0)
             if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
        preview = "; ".join(l.strip() for l in d[:DIFF_PREVIEW])
        more = f" (외 {len(d) - DIFF_PREVIEW}줄)" if len(d) > DIFF_PREVIEW else ""
        out.append(("error", "css-drift",
                    f"CSS 가 정본과 다르다 ({len(d)}줄). CSS 를 새로 짓지 말 것 — {preview}{more}"))

    body_clean = _strip_comments(body)

    if 'style="' in body_clean or "style='" in body_clean:
        out.append(("error", "inline-style",
                    "본문에 인라인 style 속성이 있다. 템플릿 클래스만 쓸 것"))

    colors = re.findall(r"#[0-9A-Fa-f]{3,8}\b|\brgba?\(", body_clean)
    if colors:
        out.append(("error", "raw-color",
                    f"본문에 색을 직접 적었다 ({', '.join(sorted(set(colors))[:4])}). "
                    "색은 t-* 클래스와 콜아웃 클래스로만"))

    defined = set(re.findall(r"\.([A-Za-z][\w-]*)", style))
    used = set()
    for attr in re.findall(r'class="([^"]*)"', body_clean):
        used.update(attr.split())
    unknown = sorted(c for c in used - defined
                     if not c.startswith(CLASS_OK_PREFIX))
    if unknown:
        out.append(("error", "unknown-class",
                    f"템플릿에 없는 클래스: {', '.join(unknown[:6])}. "
                    "새 클래스를 만들지 말고 블록 사전에서 고를 것"))

    if "language-" in body_clean and "prism" not in text.lower():
        out.append(("error", "missing-prism",
                    "language-* 코드 블록이 있는데 Prism 스크립트가 없다"))

    plain_code = re.findall(r"<pre>\s*<code(?![^>]*class=)", body_clean)
    if plain_code:
        out.append(("warn", "code-no-language",
                    f"언어 지정 없는 코드 블록 {len(plain_code)}개 — "
                    'class="language-<언어>" 를 붙이면 하이라이트된다'))

    missing = [name for name, pat in (
        ("페이지 아이콘", r'class="page-icon"'),
        ("제목(h1)", r"<h1[ >]"),
        ("메타 줄", r'class="meta"'),
        ("구분선", r"<hr\b"),
    ) if not re.search(pat, body_clean)]
    if missing:
        out.append(("warn", "header-shape",
                    f"머리 부분에 {', '.join(missing)} 이(가) 없다 (SKILL.md 1번)"))

    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="notion-doc 스타일 정본 검증기")
    ap.add_argument("files", nargs="+", type=pathlib.Path)
    ap.add_argument("--json", action="store_true", help="기계용 JSON 출력")
    args = ap.parse_args(argv)

    canon = canon_style()
    if canon is None:
        print(f"정본을 읽을 수 없다: {CANON}", file=sys.stderr)
        return 2

    report, failed = {}, False
    for f in args.files:
        if not f.is_file():
            report[str(f)] = [("error", "not-found", "파일이 없다")]
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
