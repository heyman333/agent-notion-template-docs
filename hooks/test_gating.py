#!/usr/bin/env python3
"""훅 게이팅 회귀 테스트 — 어디에 반응하고 어디에 침묵하는지 고정한다.

침묵해야 할 자리에서 말하는 훅은 훅을 끄게 만든다. 실제로 한 번 당한 오탐
("padding-left" 가 ng- 로, "max-width:" 가 th: 로 잡혀 평범한 문서가
프레임워크 템플릿으로 분류됐다)을 여기 케이스로 박아 둔다.

    python3 hooks/test_gating.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile

HOOK = pathlib.Path(__file__).resolve().parent / "notion-doc-lint.py"
ROOT = HOOK.parent.parent
DOC = '<!DOCTYPE html><html><body>{}</body></html>'

# (이름, 파일 내용 또는 기존 경로, 말해야 하는가)
CASES = [
    ("정본 그대로인 문서",      ROOT / "examples/sample.html",      False),
    ("정본 그대로인 기술 문서", ROOT / "examples/sample-tech.html",  False),
    ("skill 미적용 문서",       ROOT / "examples/before.html",       True),
    ("CSS 드리프트", None, True),
    ("지어낸 클래스", None, True),
    ("앱 껍데기",        DOC.format('<div id="root"></div><h1>App</h1>'), False),
    ("Thymeleaf 템플릿", DOC.format('<h1 th:text="${t}">x</h1>'),         False),
    ("Vue 템플릿",       DOC.format('<h1 v-if="ok">x</h1>'),              False),
    # 오탐 회귀: 평범한 문서에 흔한 CSS 속성이 프레임워크로 오인되면 안 된다
    ("padding-/width: 가 있는 평범한 문서",
     DOC.format('<style>.a{padding-left:1px;max-width:9px}</style><h1>문서</h1>'), True),
]


def fire(file_path, tool="Write"):
    payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": str(file_path)}})
    r = subprocess.run([sys.executable, str(HOOK)], input=payload,
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, f"훅은 항상 0 으로 끝나야 한다: {r.returncode}"
    return json.loads(r.stdout or "{}")


def main():
    sample = (ROOT / "examples/sample.html").read_text()
    drift = sample.replace("  .callout {\n    display: flex;",
                           "  .callout {\n    box-shadow: 0 4px 12px rgba(0,0,0,.2);\n    display: flex;")
    bad_class = sample.replace('<div class="callout callout-blue">', '<div class="hero-card">')
    synth = {"CSS 드리프트": drift, "지어낸 클래스": bad_class}

    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, content, should_speak in CASES:
            if content is None:
                content = synth[name]
            if isinstance(content, pathlib.Path):
                target = content
            else:
                target = pathlib.Path(tmp) / f"{abs(hash(name))}.html"
                target.write_text(content, encoding="utf-8")
            spoke = bool(fire(target))
            ok = spoke == should_speak
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'}  {name}: "
                  f"{'말함' if spoke else '침묵'} (기대 {'말함' if should_speak else '침묵'})")

    # 비 HTML·빌드 경로·깨진 입력은 무조건 침묵
    for name, path in [("비 HTML", ROOT / "README.md"),
                       ("node_modules 경로", ROOT / "node_modules/x.html")]:
        spoke = bool(fire(path))
        failed += spoke
        print(f"{'ok  ' if not spoke else 'FAIL'}  {name}: {'말함' if spoke else '침묵'} (기대 침묵)")
    r = subprocess.run([sys.executable, str(HOOK)], input="깨진 입력",
                       capture_output=True, text=True)
    ok = r.returncode == 0 and r.stdout.strip() == "{}"
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'}  깨진 입력: fail-open")

    print(f"\n{'실패 ' + str(failed) + '건' if failed else '전부 통과'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
