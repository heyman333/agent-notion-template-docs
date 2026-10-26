#!/usr/bin/env python3
"""Color notation is not drift (issue #7); a real color change still is."""
import notion_tokens as t


def table(v):
    return {"tokens": {"light": {"--x": v}, "dark": {}}}


SAME = [
    ("0 2px 4px rgba(15,15,15,.1)", "0 2px 4px #0f0f0f1a"),
    ("rgba(35,131,226,.57) 0px 0px 0px 1px inset", "#2383e291 0px 0px 0px 1px inset"),
    ("0px 12px 32px 0px rgba(25,25,25,.027)", "0px 12px 32px 0px #19191907"),
    ("linear-gradient(to right, rgba(135,131,120,.35), transparent)",
     "linear-gradient(to right, #87837859, #0000)"),
    ("transparent", "#0000"),
    ("#FFF", "#ffffff"),
    ("rgb(255, 255, 255)", "#fff"),
]
DIFFERENT = [
    ("rgba(15,15,15,.1)", "#0f0f0f1b"),
    ("#2c2c2b", "#2c2c2c"),
    ("0 2px 4px rgba(15,15,15,.1)", "0 3px 4px #0f0f0f1a"),
]

for old, new in SAME:
    assert not t.diff(table(old), table(new)), (old, new)
for old, new in DIFFERENT:
    assert t.diff(table(old), table(new)), (old, new)
print(f"notion_tokens diff: {len(SAME)} notation-only, {len(DIFFERENT)} real — ok")
