# markdown-docx-compiler

[![CI](https://github.com/zequn-fireworks/markdown-docx-compiler/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/zequn-fireworks/markdown-docx-compiler/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/markdown-docx-compiler)](https://pypi.org/project/markdown-docx-compiler/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)
[![Agent-friendly CLI](https://img.shields.io/badge/CLI-agent--friendly-7c3aed)](#cli-reference)

Readable markdown in, polished DOCX out.

`markdown-docx-compiler` is an AI-native, agent-friendly document compiler
that turns readable markdown into polished, editable `.docx` files optimized
for Google Docs import, final human adjustments, and easy PDF export.

## Why It Exists

- **Readable source for agents and humans** - keep documents mostly vanilla markdown instead of burying formatting in HTML or template-only syntax.
- **Small sidecars, large rendering gains** - move layout and styling into reusable YAML sidecars so the marginal LOC stays low while the rendered result looks much better.
- **DOCX as the collaboration surface** - compile into polished `.docx` for final edits in Word or Google Docs instead of treating the output as a dead render.
- **PDF-ready last mile** - once the DOCX looks right, exporting to PDF with LibreOffice, Word, or your preferred tool is straightforward.
- **Agent-friendly CLI** - noun-verb commands and `--json` output fit deep research, canvas-style drafting, and automated reporting workflows.

## Ideal Workflow

1. An agent or human drafts a report, memo, proposal, launch brief, or design review in markdown.
2. A sidecar file applies reusable layout and styling without polluting the source markdown.
3. `mdc doc create` compiles the document into polished, editable DOCX.
4. A human makes the final judgment calls in Word or Google Docs.
5. The finished DOCX can be exported to PDF as the final delivery format.

## Samples

Explore complete example document projects in the repository:

- [`goggle-offer/`][goggle-example] - fictionalized offer letter with a logo header, doc header slots, and compensation table. [Markdown][goggle-md], [Sidecar][goggle-yaml], [PDF preview][goggle-pdf]
- [`basethree-design-review/`][basethree-example] - fictionalized inference company design review with a shaded summary, decision matrix, risk register, and appendix page break. [Markdown][basethree-md], [Sidecar][basethree-yaml], [PDF preview][basethree-pdf]
- [`opena1-launch-brief/`][opena1-example] - fictionalized bilingual launch brief with centered title styling, editorial callouts, and compact tables. [Markdown][opena1-md], [Sidecar][opena1-yaml], [PDF preview][opena1-pdf]

Company names in the examples are intentionally fictionalized to avoid
trademark issues.

## Features

- **Plain markdown with optional `docx:` tags** for regions and block anchors
- **Sidecar config** for layout control (fonts, colors, column widths, per-block styling)
- **Composable sidecars** via `inherits` for reusable document defaults
- **Deterministic** table, footer, and page-level styling
- **Google Docs optimized** — import fidelity is the primary target
- **Agent-friendly CLI** with `--json` output for tool integration
- **Document-first workflow** for research reports, design docs, launch briefs, internal memos, and final editable handoff

## Quick start

```bash
pip install markdown-docx-compiler
# or install the CLI with uv / pipx
uv tool install markdown-docx-compiler
pipx install markdown-docx-compiler
```

Verify the install:

```bash
mdc --help
```

Compile a document:

```bash
mdc doc create report.md -o report.docx
```

With a sidecar config:

```bash
mdc doc create report.md --spec report.docx.yaml -o report.docx
```

If `-o` is omitted, the compiler writes `report.docx` next to `report.md`.

The compiler itself is DOCX-first. PDF export is typically the downstream step
once the generated DOCX is approved.

## How it works

Write standard markdown with optional YAML front matter for document-level defaults:

```md
---
title: Offer of Employment
font: Arial
text_color: "202124"
---

<!-- docx:doc_header.left -->
![Acme Logo](./logo.png)

<!-- docx:page_footer.center -->
2026-03-19

# Offer of Employment

Dear **Jordan Chen**, ...

## Compensation

<!-- docx:id=comp-table -->
| Component | Details |
| --- | --- |
| Base Salary | $218,000 per year |
| Equity (RSUs) | 1,400 shares over 4 years |
```

Place a sidecar YAML next to it for styling:

```yaml
document:
  font: { family: Arial, size: 10.5, color: "202124" }
  page:
    margin: { top: 0.8, bottom: 0.75, left: 1.0, right: 1.0 }

page_footer:
  font: { size: 8, color: "5F6368" }

defaults:
  paragraph:
    spacing: { after: 6, line: 1.15 }

blocks:
  comp-table:
    type: table
    table: { columns: [1fr, 3fr] }
```

Run `mdc doc create offer.md -o offer.docx` and you get a fully styled document.

Front matter only controls document-level metadata, font, link, and page
settings. Use region tags for header/footer content, and use `blocks:` anchors
for body block overrides, including blocks inside list items.

The important workflow property is that the source markdown stays readable enough for LLMs and humans to keep editing directly, while the sidecar carries the presentational complexity.

## CLI reference

```bash
mdc doc create report.md -o report.docx     # compile
mdc doc validate report.md                   # dry-run parse
mdc spec show --for report.md --resolved     # inspect merged config
mdc spec create report.docx.yaml             # scaffold a sidecar
```

Use `--json` with any command for machine-readable output.
Run `mdc doc --help` or `mdc spec --help` for detailed reference documentation.

## Development

```bash
uv sync
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/
uv build
uvx twine check dist/*
```

## Docs

- Users and agents: `mdc doc --help` and `mdc spec --help`
- Maintainers: [`AGENTS.md`][agents-doc]
- Release process: [`RELEASING.md`][releasing-doc]
- Examples: [`examples/`][examples-doc]

[agents-doc]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/AGENTS.md
[examples-doc]: https://github.com/zequn-fireworks/markdown-docx-compiler/tree/main/examples
[goggle-example]: https://github.com/zequn-fireworks/markdown-docx-compiler/tree/main/examples/goggle-offer
[goggle-md]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/goggle-offer/offer.md
[goggle-pdf]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/goggle-offer/offer.pdf
[goggle-yaml]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/goggle-offer/offer.docx.yaml
[basethree-example]: https://github.com/zequn-fireworks/markdown-docx-compiler/tree/main/examples/basethree-design-review
[basethree-md]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/basethree-design-review/design-review.md
[basethree-pdf]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/basethree-design-review/design-review.pdf
[basethree-yaml]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/basethree-design-review/design-review.docx.yaml
[opena1-example]: https://github.com/zequn-fireworks/markdown-docx-compiler/tree/main/examples/opena1-launch-brief
[opena1-md]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/opena1-launch-brief/launch-brief.md
[opena1-pdf]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/opena1-launch-brief/launch-brief.pdf
[opena1-yaml]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/opena1-launch-brief/launch-brief.docx.yaml
[releasing-doc]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/RELEASING.md
