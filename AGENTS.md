# markdown-docx-compiler — Maintainer Guide

This `AGENTS.md` is for agents and contributors **refining the repository
itself**.

If an agent is **using** the installed package to compile documents, run
`mdc <noun> --help` for usage documentation (e.g. `mdc doc --help`).

## Repo purpose

`markdown-docx-compiler` is a standalone compiler that turns AI-authored
markdown into polished `.docx` files optimized for later Google Docs import and
human editing.

The architecture is intentionally:

- markdown parser front-end
- typed document IR
- sidecar-driven style resolution
- custom DOCX backend with explicit layout control

This repo is **not** a generic markdown renderer and should stay focused on the
document-compiler use case.

## Key principles

When changing the repo, preserve these assumptions:

1. Keep source markdown as vanilla-compatible as possible.
2. Put advanced layout control in sidecar config, not custom inline syntax.
3. Optimize for Google Docs import fidelity rather than Word-perfect output.
4. Prefer deterministic document structure over clever or lossy formatting.
5. Keep the compiler standalone and repo-agnostic.

## Repo structure

- `src/markdown_docx_compiler/compile.py` — top-level compiler orchestration
- `src/markdown_docx_compiler/parser/markdown.py` — markdown parser (produces `models.document` IR)
- `src/markdown_docx_compiler/parser/front_matter.py` — YAML front matter extraction
- `src/markdown_docx_compiler/models/` — typed document IR, config, and style dataclasses
- `src/markdown_docx_compiler/models/loader.py` — sidecar YAML loading into config models
- `src/markdown_docx_compiler/resolve/` — 3-tier style cascade (defaults, sidecar, front matter)
- `src/markdown_docx_compiler/backend/docx/doc_renderer.py` — top-level DOCX renderer
- `src/markdown_docx_compiler/backend/docx/blocks.py` — block-level rendering
- `src/markdown_docx_compiler/backend/docx/inlines.py` — inline-level rendering
- `src/markdown_docx_compiler/backend/docx/regions.py` — region rendering (headers, footers)
- `src/markdown_docx_compiler/backend/docx/ooxml_helpers.py` — low-level OOXML XML helpers
- `src/markdown_docx_compiler/resolve/defaults.py` — built-in document and block defaults
- `src/markdown_docx_compiler/cli/` — noun-verb CLI (`mdc doc`, `mdc spec`)
- `src/markdown_docx_compiler/help_text.py` — help topic aggregator and sidecar reference

- `examples/` — sample documents with sidecar configs and preview images
- `tests/fixtures/` — markdown and sidecar fixture inputs
- `tests/figures/` — image assets used by fixtures
- `tests/manual_review_output/` — generated review artifacts, ignored by git

## Help text co-location

Each module owns its user-facing help topic text. The CLI aggregates them via
`help_text.py`. When changing a module's behavior, update its `HELP_TOPIC`
constant to stay in sync.

## Change discipline

If you refine the compiler:

- update or add fixtures when behavior changes
- keep each module's `HELP_TOPIC` in sync with its actual behavior
- prefer extending the IR or sidecar model over adding markdown-only hacks
- do not introduce package-specific inline directives lightly
- keep benchmark and showcase fixtures compiling cleanly

## Validation

Before finishing substantive changes, run:

```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/
```

## Acceptance criteria

### Fixtures

Core fixture:

- `tests/fixtures/sample_report.md` + `sample_report.docx.yaml`

Review fixtures for visual verification:

- `tests/fixtures/showcase_en.md` + `showcase_en.docx.yaml`
- `tests/fixtures/showcase_zh.md` + `showcase_zh.docx.yaml`
- `tests/fixtures/benchmark_en.md`
- `tests/fixtures/benchmark_zh.md`

Compile all review fixtures:

```bash
uv run python tests/compile_review_fixtures.py
```

### Automated checks

Key expectations tested by `uv run pytest tests/`:

- sample report compiles successfully
- generated DOCX contains fixed-layout table XML
- generated DOCX contains explicit width tags
- footer contains configured text and `PAGE` field code
- image is embedded into `word/media/`

### Manual Google Docs import checks

For each release candidate:

1. Compile the sample fixture to `.docx`
2. Upload/import into Google Docs
3. Verify:
   - headings look hierarchical
   - lead paragraph looks distinct from body text
   - benchmark table spans the page width acceptably
   - table columns preserve a visible width difference
   - table borders are visible
   - code block background and monospace text survive import
   - blockquote is visually distinct
   - image appears and caption remains readable
   - footer text and page numbering behave in pages mode
   - CJK text is readable and not obviously broken

### Exit criteria

The fixture set passes when:

- automated tests pass locally
- no structural DOCX regression is found
- Google Docs import keeps the document at least 90% ready for human editing

## Avoid

- coupling the compiler to repo-specific wrappers
- adding unsupported markdown features without tests and help text updates
- changing the authoring contract silently
