# markdown-docx-compiler

A standalone compiler that turns AI-authored markdown into polished `.docx`
files optimized for Google Docs import and human editing.

## Samples

Explore complete example document projects in the repository:

- [`google-offer/`][google-example] - fictionalized offer letter with a logo
  header and compensation table. [Markdown][google-md], [Sidecar][google-yaml],
  [PDF preview][google-pdf]
- [`openai-offer/`][openai-example] - fictionalized offer letter with a
  two-column header and equity section. [Markdown][openai-md],
  [Sidecar][openai-yaml], [PDF preview][openai-pdf]

Company names in the examples are intentionally fictionalized to avoid
trademark issues.

## Features

- **Vanilla markdown in, polished DOCX out** — no custom syntax required
- **Sidecar config** for layout control (fonts, colors, column widths, per-block styling)
- **Composable sidecars** via `inherits` for reusable document defaults
- **Deterministic** table, footer, and page-level styling
- **Google Docs optimized** — import fidelity is the primary target
- **Agent-friendly CLI** with `--json` output for tool integration

## Quick start

```bash
pip install markdown-docx-compiler
# or install the CLI with uv
uv tool install markdown-docx-compiler
```

Compile a document:

```bash
mdc doc create report.md -o report.docx
```

With a sidecar config:

```bash
mdc doc create report.md --spec report.docx.yaml -o report.docx
```

If `-o` is omitted, the compiler writes `<input>.docx` next to the markdown
file.

## How it works

Write standard markdown with optional YAML front matter:

```md
---
title: Offer of Employment
logo_path: ./logo.png
footer_center: "2026-03-19"
---

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

## CLI reference

```bash
mdc doc create report.md -o report.docx     # compile
mdc doc validate report.md                   # dry-run parse
mdc spec show --for report.md --resolved     # inspect merged config
mdc spec create report.docx.yaml             # scaffold a sidecar
```

Use `--json` with any command for machine-readable output.
Run `mdc <noun> --help` for detailed reference documentation.

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

- Users and agents: `mdc <noun> --help` (e.g. `mdc doc --help`, `mdc spec --help`)
- Maintainers: [`AGENTS.md`][agents-doc]
- Release process: [`RELEASING.md`][releasing-doc]
- Examples: [`examples/`][examples-doc]

[agents-doc]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/AGENTS.md
[examples-doc]: https://github.com/zequn-fireworks/markdown-docx-compiler/tree/main/examples
[google-example]: https://github.com/zequn-fireworks/markdown-docx-compiler/tree/main/examples/google-offer
[google-md]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/google-offer/offer.md
[google-pdf]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/google-offer/offer.pdf
[google-yaml]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/google-offer/offer.docx.yaml
[openai-example]: https://github.com/zequn-fireworks/markdown-docx-compiler/tree/main/examples/openai-offer
[openai-md]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/openai-offer/offer.md
[openai-pdf]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/openai-offer/offer.pdf
[openai-yaml]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/examples/openai-offer/offer.docx.yaml
[releasing-doc]: https://github.com/zequn-fireworks/markdown-docx-compiler/blob/main/RELEASING.md
