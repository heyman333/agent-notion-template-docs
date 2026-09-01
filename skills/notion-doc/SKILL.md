---
name: notion-doc
description: Notion design skill that MUST be used whenever creating documents. When the user asks for a document, report, summary, meeting notes, or review write-up in HTML/Markdown, load this skill first. The content decides the document's structure and outline; this skill only governs the Notion blocks (callouts, toggles, tables, checklists, code, columns, etc.) and visual style.
---

# Creating documents with Notion's design

**This skill governs only how the document *looks*.** The outline, sections,
and flow are decided by the content and the request — no particular document
format (proposal, etc.) is imposed. Instead, every document is rendered with
the blocks and design language Notion provides.

## 1. Header area (required)

1. **Page icon**: one emoji matching the document's topic, large, above the title (Notion page icon)
2. **Title**: a short noun phrase
3. **Meta line**: date · author · 1–2 tag pills
4. A thin divider below the meta line

## 2. Notion block dictionary — pick the block that fits the content

| Content | Block |
|---|---|
| Key takeaway, the one line to emphasize | Callout (blue 💡) |
| Reference, supplementary info | Callout (gray) |
| Done, success, what went well | Callout (green ✅) |
| Caution, constraints | Callout (yellow ⚠️) |
| Warning, incident, risk | Callout (red 🚨) |
| Opening of a long document (4+ h2s) | Table of contents (`toc`) |
| Parent document, location context | breadcrumb |
| Comparable, listable facts | simple table |
| Two chunks that belong side by side | 2-column layout |
| Long details or logs that break the flow | `<details>` toggle |
| Tasks, progress | checkbox list (done items get strikethrough) |
| Code | code block + `class="language-<lang>"` syntax highlighting (required) |
| One striking sentence | quote (bold left bar) |
| Introducing an external link | bookmark card |
| A single call-to-action link | button block (`btn`) |
| Word-level emphasis | **bold**, inline code, Notion text colors (`t-blue` etc., 5 colors) |

Never use blocks as decoration — only when they match a purpose in this table.

## 3. Visual style

**HTML documents MUST start from the `template.html` skeleton in this skill's
directory.** Do not write new CSS; use the template's classes as they are. The
template's palette and dimensions are Notion's actual design-token values
(see the comment next to each value). Core rules:

- 720px content width, centered, generous whitespace — measured values as-is
- Text color `#2C2C2B`, 16px/1.5, white background, minimal decoration. No shadows, gradients, or heavy background colors
- Rounded corners use only the `--radius` (10px) token — shared by callouts, bookmarks, and code blocks
- Colors come only from the template's tokens (5 callout colors, 5 text colors, `--tok-*` code tokens) — no new colors
- Light/dark palettes are built in as CSS tokens and follow the viewer's theme automatically
- Code highlighting is handled by the Prism scripts at the bottom of the template — just add the `language-*` class
- Korean line breaking (`word-break: keep-all`) and print/PDF rules
  (`@media print`) are already in the template — do not add your own. The dark
  palette is wrapped in `@media screen`, so printing automatically falls back
  to light

For Markdown documents, apply the same sensibility: emoji + title (h1), a meta
line, callouts as `> emoji **Title** — body` quotes, tasks as `- [ ]`
checklists, code in language-tagged fences.

## 4. Verify after writing

After writing an HTML document, check it with `lint.py` from this skill's directory.

```bash
python3 <skill directory>/lint.py doc.html
```

- `css-drift` — you modified the template's `<style>`. Restore it and change only the body
- `unknown-class` — you invented a class. Pick one from the block dictionary in section 2
- `inline-style` · `raw-color` — you styled or colored the body directly. Use template classes instead

## 5. Interaction with other skills

- When publishing as an Artifact, also load `artifact-design` as required, but
  **this skill's style tokens take precedence** (take only the technical
  requirements — responsiveness, dark mode — from artifact-design)
- If charts are included, follow the `dataviz` skill's color and mark rules, but keep the layout inside this template
