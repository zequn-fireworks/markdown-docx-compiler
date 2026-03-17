# markdown-docx-compiler

A standalone compiler for turning AI-authored markdown into polished `.docx`
documents designed to import cleanly into Google Docs for final human editing.

This is not a generic markdown converter. It optimizes for:

- vanilla-markdown-friendly source documents
- external sidecar config for layout control (column widths, themes, per-block styling)
- deterministic table, footer, and page-level styling
- agent-friendly CLI with JSON output

## Quick start

```bash
uv run mdc compile report.md -o report.docx
```

With a sidecar config:

```bash
uv run mdc compile report.md --spec report.docx.yaml -o report.docx
```

Need usage documentation?

```bash
uv run mdc help
uv run mdc help sidecar
uv run mdc help themes
```

## Example

`report.md`

```md
---
title: Benchmark Report
theme: fireworks
footer_center: 2026-03-16
---

# Benchmark Report

This is the opening summary paragraph.

<!-- docx:id=results-table -->
| Model | TTFT | TPS |
| --- | ---: | ---: |
| A | 120 | 80 |
```

`report.docx.yaml`

```yaml
document:
  footer:
    right: Draft

selectors:
  - match:
      type: paragraph
      heading: "Benchmark Report"
    apply:
      variant: lead

blocks:
  results-table:
    variant: benchmark
    columns: [3fr, 1fr, 1fr]
```

## Development

```bash
uv sync
uv run pytest
```

## Docs

- Installed users and agents: `mdc help` and `mdc help <topic>`
- Repository maintainers and contributors: `AGENTS.md`
