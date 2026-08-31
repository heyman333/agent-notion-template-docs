# 📄 notion-doc

> Make your AI agent write documents like Notion — not like an AI.

[![notion-sync](https://github.com/heyman333/agent-notion-template-docs/actions/workflows/notion-sync.yml/badge.svg)](https://github.com/heyman333/agent-notion-template-docs/actions/workflows/notion-sync.yml)

[한국어](README.ko.md)

Ask an AI agent for a document and you get the same look every time: a purple
gradient hero, emoji-studded headers, cards with drop shadows. **notion-doc**
is an agent skill that replaces that with Notion's design language — same
request, same content, completely different result:

| Without notion-doc | With notion-doc |
|---|---|
| ![before](docs/screenshot-before.png) | ![after](docs/screenshot-light.png) |

It stays out of your document's content and structure — the outline is up to
you (and your agent). The skill only governs how it looks.

## What you get

**The Notion block set**

- Emoji page icon, tag pills, meta line
- Callouts in 4 colors — blue (key point), gray (note), yellow (caution), red (warning)
- Simple tables, 2-column layout
- Toggles (`<details>`), checklists with strikethrough, quotes, bookmark cards
- Code blocks with syntax highlighting (Prism, themed for light & dark), inline code
- Notion's 5 text colors (blue · red · orange · green · purple)

**One style canon** — the agent never generates CSS. It copies
[`template.html`](skills/notion-doc/template.html) — 708px content width,
`#37352F` text, the full Notion light/dark palette as CSS tokens — and only
fills in content. Dark mode follows the viewer automatically:

| Light | Dark |
|---|---|
| ![light](docs/screenshot-light.png) | ![dark](docs/screenshot-dark.png) |

## Install

**Claude Code (plugin, recommended)**

```
/plugin marketplace add heyman333/agent-notion-template-docs
/plugin install notion-doc@agent-notion-template-docs
```

**Claude Code (manual copy)**

```bash
# this project only
cp -r skills/notion-doc <your-project>/.claude/skills/

# every project
cp -r skills/notion-doc ~/.claude/skills/
```

**Codex, Cursor, Gemini CLI, and others**

The skill is two plain files with nothing Claude-specific — any agent that
reads instruction files can use it. See
[Using with other agents](docs/using-with-other-agents.md) for ready-to-paste
snippets (`AGENTS.md`, `.cursor/rules`, `GEMINI.md`).

## Usage

Once installed, it applies automatically whenever you ask for a document
("write this up as a report", "summarize this as a doc", "write a postmortem").
To invoke it explicitly in Claude Code:

```
/notion-doc:notion-doc
```

## Examples

Open these in a browser — the screenshots above are `sample.html`.

| File | Content | Blocks shown |
|---|---|---|
| [`sample.html`](examples/sample.html) | Campaign proposal (Korean) | Callouts, tables, toggle, checklist |
| [`sample-tech.html`](examples/sample-tech.html) | Incident analysis (Korean) | Syntax-highlighted code, red/yellow callouts |
| [`sample-en.html`](examples/sample-en.html) | Campaign proposal (English) | Same design, English document |
| [`before.html`](examples/before.html) | The "without" side of the comparison | What agents produce by default |

## Repo layout

```
.claude-plugin/
  plugin.json          # plugin manifest
  marketplace.json     # marketplace catalog
skills/notion-doc/
  SKILL.md             # the rules: block dictionary + visual constraints
  template.html        # the style canon: block CSS + light/dark palette tokens
examples/              # rendered example documents
docs/
  using-with-other-agents.md
```

## Staying in sync with Notion

Notion keeps shipping new blocks and quietly adjusting its design. This repo
watches for that instead of promising to: a weekly CI job
([`notion-sync`](.github/workflows/notion-sync.yml)) re-fetches public
reference pages two ways — **block types** via Notion's page API (cursor-
paginated, ~24 block types watched), and **coarse style tokens** (colors,
widths) via a headless render — and diffs both against the committed baseline
[`sync/notion-snapshot.json`](sync/notion-snapshot.json).

Reference pages:
- [Notion Block Reference — All of Notion's Blocks](https://thomasfrank.notion.site/8b40147600284c60b6f708e38f16ee68)
  (Thomas Frank's public block zoo — broad coverage)
- [this project's own page](https://cautious-shovel-8bd.notion.site/3ccb975b320f80128e94c05534b4df9d)
  (under our control, for blocks the zoo lacks)

- Badge green = the skill matches what Notion currently renders
- On drift, the job fails and opens an issue with the exact diff, including
  whether a new block type is already covered by the skill or needs work

As the reference page grows more block types, the watch gets stricter for free.

## Design source

The visual reference is Notion itself. Public page used as reference:
https://cautious-shovel-8bd.notion.site/3ccb975b320f80128e94c05534b4df9d

## License

[MIT](LICENSE)
