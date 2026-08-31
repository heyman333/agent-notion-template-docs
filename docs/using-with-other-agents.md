# Using notion-doc with other agents

The skill has no Claude-specific magic. It is two plain files, plus an
optional checker:

- [`skills/notion-doc/SKILL.md`](../skills/notion-doc/SKILL.md) — the rules: header layout, a block dictionary (which content goes in which Notion block), visual constraints
- [`skills/notion-doc/template.html`](../skills/notion-doc/template.html) — the style canon: every block's CSS, Notion light/dark palette tokens, Prism syntax highlighting
- [`skills/notion-doc/lint.py`](../skills/notion-doc/lint.py) — optional: checks a generated document against the canon. Standard library only, no Claude Code required

Any agent that reads instruction files can use them. The recipe is always the same:

1. Copy `skills/notion-doc/` into your repo (e.g. `docs/notion-doc/`)
2. In your agent's instruction file, tell it to follow `SKILL.md` when generating documents and to start HTML documents from `template.html`
3. Optional but recommended: have the agent run `python3 docs/notion-doc/lint.py <file>` after writing, and fix whatever it reports

Below are ready-to-paste snippets per agent.

## OpenAI Codex

Append to `AGENTS.md` at the repo root:

```markdown
## Document generation

When asked to produce a document (report, write-up, summary, meeting notes)
as HTML or Markdown, first read `docs/notion-doc/SKILL.md` and follow it.
For HTML output, copy `docs/notion-doc/template.html` as the starting point
and only fill in content — do not write new CSS.
```

## Cursor

Create `.cursor/rules/notion-doc.mdc`:

```markdown
---
description: Notion-style document generation rules
alwaysApply: false
globs:
---
When generating a document (report, write-up, summary, meeting notes) as
HTML or Markdown, follow @docs/notion-doc/SKILL.md. For HTML output, start
from @docs/notion-doc/template.html and only fill in content — never write
new CSS.
```

## Gemini CLI

Append to `GEMINI.md` at the repo root — same text as the Codex snippet above.

## Claude Code (without the plugin)

```bash
# this project only
cp -r skills/notion-doc <your-project>/.claude/skills/

# every project
cp -r skills/notion-doc ~/.claude/skills/
```

Claude Code picks it up as a skill automatically; the instruction-file snippet
is not needed.

## Notes

- `SKILL.md` is currently written in Korean. Every agent above handles that
  fine, but a translated copy works just as well if you prefer — the rules,
  not the language, are what matters.
- The template loads Prism from cdnjs for code highlighting. If your
  environment blocks external scripts, delete the two `<script>` tags at the
  bottom of `template.html`; code blocks degrade to plain monospace.
