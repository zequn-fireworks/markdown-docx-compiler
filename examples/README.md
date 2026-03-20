# Examples

Each subdirectory is a self-contained document project showing how
`markdown-docx-compiler` turns markdown + sidecar config into a styled DOCX.

| Example | Description |
|---------|-------------|
| `google-offer/` | Formal offer letter with company logo header and compensation table |
| `openai-offer/` | Offer letter with two-column doc header and equity details |

> **Note:** Company names are fictionalized ("Goggle", "OpenA1") to avoid
> trademark issues. These examples are for demonstration purposes only.

## Structure

Each example contains:

- `offer.md` — source markdown with front matter and region tags
- `offer.docx.yaml` — sidecar config controlling fonts, spacing, and layout
- `logo.png` — company logo referenced by the page header
- `offer.docx` — pre-compiled output (regenerate with the command below)
- `offer.pdf` — PDF rendering of the compiled document

## Recompiling

From the repo root:

```bash
uv run mdc doc create examples/google-offer/offer.md
uv run mdc doc create examples/openai-offer/offer.md
```
