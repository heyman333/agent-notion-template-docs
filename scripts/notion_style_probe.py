#!/usr/bin/env python3
"""Notion block→token style mapper.

notion_tokens.py knows every palette value Notion ships, but not which token
each block type actually paints with — block backgrounds are applied by React
as inline styles, not by any stylesheet rule. This probe closes that gap:

1. Render the reference page (Playwright, light scheme).
2. For every block, find the element that actually paints (first descendant
   with a non-transparent background) and record its computed styles —
   colors, radius, padding, fonts, borders. Raw measured values, no guessing.
3. Reverse-map each measured color into the light token table
   (sync/notion-tokens.json) → token name(s).
4. Derive the dark value for each mapped color by looking the same token up
   in the dark table. (The page itself only serves light; flipping the theme
   class wouldn't move inline-styled backgrounds, so token lookup is the
   only faithful dark source.)

Output: sync/notion-style-map.json — per-block measured geometry + the
light→token→dark color mapping. This file is what template.html's values
should trace back to.

Usage:
  notion_style_probe.py [--out FILE] [--tokens FILE]
"""
import argparse
import datetime
import json
import pathlib
import re

REFERENCE_URL = "https://thomasfrank.notion.site/8b40147600284c60b6f708e38f16ee68"
ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKENS = ROOT / "sync" / "notion-tokens.json"
OUT = ROOT / "sync" / "notion-style-map.json"

PROBE_JS = r"""
() => {
  const cs = el => getComputedStyle(el);
  const painted = c => c && c !== 'transparent' && !/^rgba\(\d+, \d+, \d+, 0\)$/.test(c);

  // First element (BFS from root) that actually paints a background.
  const paintedEl = root => {
    const q = [root];
    while (q.length) {
      const el = q.shift();
      if (painted(cs(el).backgroundColor)) return el;
      q.push(...el.children);
    }
    return null;
  };
  // First descendant with real text — carries the block's font styling.
  const textEl = root => {
    const q = [root];
    while (q.length) {
      const el = q.shift();
      if ([...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return el;
      q.push(...el.children);
    }
    return null;
  };
  const box = el => {
    const s = cs(el);
    return {
      background: s.backgroundColor, border_radius: s.borderRadius,
      padding: `${s.paddingTop} ${s.paddingRight} ${s.paddingBottom} ${s.paddingLeft}`,
    };
  };
  const font = el => {
    const s = cs(el);
    return { color: s.color, font_size: s.fontSize, line_height: s.lineHeight,
             font_weight: s.fontWeight, font_family: s.fontFamily };
  };
  // First descendant with a visible border on the given side.
  const borderEl = (root, side) => {
    const q = [root];
    while (q.length) {
      const el = q.shift();
      const s = cs(el);
      if (parseFloat(s[`border${side}Width`]) > 0 &&
          s[`border${side}Style`] !== 'none') return el;
      q.push(...el.children);
    }
    return null;
  };

  const result = { page: {}, blocks: {} };

  const content = document.querySelector('.notion-page-content');
  const scroller = document.querySelector('.notion-page-block')?.closest('[class*="scroller"]');
  const bodyS = cs(document.body);
  result.page = {
    body_background: bodyS.backgroundColor,
    body_color: bodyS.color,
    body_font_family: bodyS.fontFamily,
    content_rect_width: content ? Math.round(content.getBoundingClientRect().width) : null,
    content_padding: content ? `${cs(content).paddingLeft} / ${cs(content).paddingRight}` : null,
    content_font: content ? font(textEl(content) || content) : null,
  };
  const title = document.querySelector('.notion-page-block h1, h1.notion-record-icon ~ *, [class*="notion-page"] h1')
             || document.querySelector('h1');
  if (title) result.page.title_font = font(title);

  // Every rendered block, grouped by notion-<type>-block class.
  const seen = {};
  for (const el of document.querySelectorAll('[class*="notion-"][class*="-block"]')) {
    const m = el.className.match?.call ? String(el.className).match(/notion-([a-z_]+)-block/) : null;
    if (!m) continue;
    const type = m[1];
    seen[type] = seen[type] || [];
    if (seen[type].length >= 6) continue;   // enough samples per type

    const entry = { text_preview: (el.textContent || '').trim().slice(0, 60) };
    const bgEl = paintedEl(el);
    if (bgEl) {
      entry.painted = box(bgEl);
      // Notion writes tokens straight into inline styles (background: var(--c-…)) —
      // when present, that token name is authoritative, no value-matching needed.
      const declared = (bgEl.getAttribute('style') || '')
        .match(/background[^;]*var\((--[A-Za-z0-9_-]+)/);
      if (declared) entry.painted.background_token_declared = declared[1];
    }
    const tEl = textEl(el);
    if (tEl) {
      entry.font = font(tEl);
      const declared = (tEl.getAttribute('style') || '')
        .match(/(?:^|;)\s*color[^;]*var\((--[A-Za-z0-9_-]+)/);
      if (declared) entry.font.color_token_declared = declared[1];
    }

    if (type === 'quote') {
      const b = borderEl(el, 'Left') || el.querySelector('blockquote') || el;
      const s = cs(b);
      entry.border_left = `${s.borderLeftWidth} ${s.borderLeftStyle} ${s.borderLeftColor}`;
      if (s.boxShadow !== 'none') entry.box_shadow = s.boxShadow;
      entry.quote_padding = `${s.paddingTop} ${s.paddingRight} ${s.paddingBottom} ${s.paddingLeft}`;
    }
    if (type === 'text' && !result.page.block_rect_width) {
      // actual text column width — the page-content rect includes gutters
      result.page.block_rect_width = Math.round(el.getBoundingClientRect().width);
    }
    if (type === 'divider') {
      const b = borderEl(el, 'Bottom') || borderEl(el, 'Top');
      if (b) { const s = cs(b);
               entry.border = `${s.borderBottomWidth || s.borderTopWidth} ${s.borderBottomColor || s.borderTopColor}`; }
      else if (bgEl) entry.border = `bg ${cs(bgEl).backgroundColor} h=${bgEl.getBoundingClientRect().height}`;
    }
    if (type === 'table') {
      const td = el.querySelector('td');
      const th = el.querySelector('tr:first-child td, tr:first-child th');
      if (td) { const s = cs(td);
                entry.cell = { border: `${s.borderTopWidth} ${s.borderTopColor}`,
                               padding: `${s.paddingTop} ${s.paddingRight} ${s.paddingBottom} ${s.paddingLeft}`,
                               font_size: s.fontSize }; }
      if (th) entry.header_row_background = cs(th).backgroundColor;
    }
    if (type === 'to_do') {
      for (const c of el.querySelectorAll('div,svg,input')) {
        const s = cs(c); const r = c.getBoundingClientRect();
        if (r.width > 8 && r.width < 24 && r.width === r.height && painted(s.backgroundColor)) {
          entry.checkbox = { background: s.backgroundColor, size: Math.round(r.width) }; break;
        }
      }
    }
    if (type === 'header' || type === 'sub_header' || type === 'sub_sub_header') {
      const s = tEl ? cs(tEl) : null;
      if (s) entry.heading = { font_size: s.fontSize, font_weight: s.fontWeight,
                               line_height: s.lineHeight,
                               margin_top: cs(el).marginTop };
    }
    seen[type].push(entry);
  }
  result.blocks = seen;

  // Inline styling that lives on spans, not blocks: inline code and links.
  for (const sp of document.querySelectorAll('.notion-page-content span, .notion-page-content code')) {
    const s = cs(sp);
    if (!result.inline_code && /monospace|SFMono|Consolas/i.test(s.fontFamily) &&
        painted(s.backgroundColor)) {
      result.inline_code = { color: s.color, background: s.backgroundColor,
                             font_size: s.fontSize, border_radius: s.borderRadius,
                             padding: `${s.paddingTop} ${s.paddingRight} ${s.paddingBottom} ${s.paddingLeft}`,
                             font_family: s.fontFamily,
                             text_preview: sp.textContent.trim().slice(0, 40) };
    }
  }
  const link = document.querySelector('.notion-page-content a[href]');
  if (link) {
    const s = cs(link);
    result.link = { color: s.color, text_decoration: s.textDecorationLine,
                    decoration_color: s.textDecorationColor, opacity: s.opacity };
  }

  // Full inventory of tokens Notion's renderer references from inline styles:
  // "<block type> <css property> → var(--token)", with usage counts. This is
  // the block→token map straight from the horse's mouth.
  const inventory = {};
  for (const el of document.querySelectorAll('[style*="var(--"]')) {
    const blockEl = el.closest('[class*="notion-"][class*="-block"]');
    const bm = blockEl ? String(blockEl.className).match(/notion-([a-z_]+)-block/) : null;
    const block = bm ? bm[1] : '(page chrome)';
    for (const dm of (el.getAttribute('style') || '')
                       .matchAll(/([a-z-]+)\s*:[^;]*var\((--[A-Za-z0-9_-]+)/g)) {
      const key = `${block} ${dm[1]} → var(${dm[2]})`;
      inventory[key] = (inventory[key] || 0) + 1;
    }
  }
  result.inline_token_inventory = Object.fromEntries(
    Object.entries(inventory).sort((a, b) => a[0].localeCompare(b[0])));
  return result;
}
"""

EXPAND_TOGGLES_JS = r"""
() => {
  // Open every collapsed toggle so blocks hidden inside get rendered.
  let clicked = 0;
  for (const t of document.querySelectorAll('.notion-toggle-block')) {
    const btn = t.querySelector('div[role="button"]');
    if (btn && btn.getAttribute('aria-expanded') !== 'true') { btn.click(); clicked++; }
  }
  return clicked;
}
"""

HEX = re.compile(r"^#([0-9a-fA-F]{3,8})$")


def normalize(color):
    """'#f9f8f7' / 'rgb(249, 248, 247)' / 'rgba(x,y,z,.5)' → comparable tuple."""
    color = color.strip().lower()
    m = HEX.match(color)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (r, g, b, round(a, 3))
    m = re.match(r"rgba?\(([^)]+)\)", color)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        r, g, b = (int(float(p)) for p in parts[:3])
        a = float(parts[3]) if len(parts) > 3 else 1.0
        return (r, g, b, round(a, 3))
    return None


def token_index(table):
    idx = {}
    for name, value in table.items():
        n = normalize(value)
        if n:
            idx.setdefault(n, []).append(name)
    return idx


def map_color(measured, light_idx, dark_table, hint=None):
    """Measured light color → {tokens, dark candidates}. hint ranks token names
    ('Bac' for backgrounds, 'Tex' for text, 'Bor' for borders) first."""
    n = normalize(measured)
    if n is None:
        return None
    names = light_idx.get(n, [])
    if hint:
        names = sorted(names, key=lambda s: (hint not in s, s))
    return {
        "light": measured,
        "tokens": names,
        "dark": {name: dark_table[name] for name in names if name in dark_table},
    } if names else {"light": measured, "tokens": [], "dark": {}}


def annotate(probe, tokens):
    light_idx = token_index(tokens["light"])
    light, dark = tokens["light"], tokens["dark"]
    hints = {"background": "Bac", "color": "Tex", "header_row_background": "Bac"}

    def walk(obj):
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                out[k] = walk(v)
                if isinstance(v, str) and k.endswith("_token_declared"):
                    out[k + "@resolved"] = {
                        "light": light.get(v),
                        "dark": dark.get(v, light.get(v)),  # absent in dark = same value
                    }
                elif isinstance(v, str) and ("color" in k or "background" in k):
                    mapped = map_color(v, light_idx, dark, hints.get(k))
                    if mapped and mapped["tokens"]:
                        out[k + "@token"] = mapped
            return out
        if isinstance(obj, list):
            return [walk(v) for v in obj]
        return obj

    return walk(probe)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--tokens", default=str(TOKENS))
    args = parser.parse_args()

    tokens = json.loads(pathlib.Path(args.tokens).read_text(encoding="utf-8"))["tokens"]

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        tab = browser.new_page(viewport={"width": 1280, "height": 2200})
        tab.emulate_media(color_scheme="light")
        # networkidle never fires on notion.site (live websockets) — wait for the DOM
        tab.goto(REFERENCE_URL, wait_until="domcontentloaded", timeout=60000)
        tab.wait_for_selector(".notion-page-content", timeout=45000)
        tab.wait_for_timeout(3000)  # let late-hydrating blocks settle
        for _ in range(4):  # nested toggles need repeated passes
            if tab.evaluate(EXPAND_TOGGLES_JS) == 0:
                break
            tab.wait_for_timeout(1200)
        probe = tab.evaluate(PROBE_JS)
        browser.close()

    result = {
        "probed_at": datetime.date.today().isoformat(),
        "reference_url": REFERENCE_URL,
        "note": "measured on the light render; dark values derived by token lookup",
        **annotate(probe, tokens),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n_blocks = sum(len(v) for v in result["blocks"].values())
    print(f"{len(result['blocks'])} block types / {n_blocks} samples → {out}")


if __name__ == "__main__":
    main()
