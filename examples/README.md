# Examples

Each subdirectory is a self-contained document project showing how
`markdown-docx-compiler` turns markdown + sidecar config into a styled DOCX.

| Example | Description |
|---------|-------------|
| `goggle-offer/` | Formal offer letter with company logo header, doc header slots, and compensation table |
| `basethree-design-review/` | Engineering design review with shaded summary, wide decision table, risk register, code block, and appendix page break |
| `opena1-launch-brief/` | Bilingual launch brief with centered title styling, editorial callouts, compact tables, and minimal region chrome |

> **Note:** Company names are fictionalized ("Goggle", "Basethree", "OpenA1") to avoid
> trademark issues. These examples are for demonstration purposes only.

## Structure

Each example contains:

- a primary markdown source file (`offer.md`, `design-review.md`, or `launch-brief.md`)
- a matching sidecar config (`*.docx.yaml`) controlling fonts, spacing, and layout
- `logo.png` or another image asset referenced by the document
- a generated `.docx` output
- a generated `.pdf` rendering of that output

## Recompiling

From the repo root:

```bash
uv run mdc doc create examples/goggle-offer/offer.md
uv run mdc doc create examples/basethree-design-review/design-review.md
uv run mdc doc create examples/opena1-launch-brief/launch-brief.md
```
