#!/usr/bin/env python3
"""docs/ 스크린샷을 examples/ 에서 다시 찍는다.

라이트·다크가 같은 문서·같은 뷰포트·같은 배율로 나오도록 한 곳에서 관리한다.

    pip install playwright && playwright install chromium
    python scripts/shoot_screenshots.py
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIDTH = 1000
SCALE = 2

# (출력 파일, 소스 예제, 테마)
SHOTS = [
    ("screenshot-light.png", "examples/sample.html", "light"),
    ("screenshot-dark.png", "examples/sample.html", "dark"),
    ("screenshot-tech.png", "examples/sample-tech.html", "light"),
    ("screenshot-before.png", "examples/before.html", "light"),
]


def main() -> int:
    out_dir = ROOT / "docs"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for out, src, theme in SHOTS:
            page = browser.new_page(
                viewport={"width": WIDTH, "height": 900},
                device_scale_factor=SCALE,
                color_scheme=theme,
            )
            page.goto((ROOT / src).as_uri())
            page.evaluate(
                "t => document.documentElement.setAttribute('data-theme', t)", theme
            )
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(600)  # Prism 하이라이트 적용 대기
            page.screenshot(path=out_dir / out, full_page=True)
            height = page.evaluate("document.documentElement.scrollHeight")
            print(f"{out:26} {src:28} {theme:5} {WIDTH}x{height} @{SCALE}x")
            page.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
