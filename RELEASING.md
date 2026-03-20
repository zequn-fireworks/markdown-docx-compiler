# Releasing `markdown-docx-compiler`

This repository is set up to publish to PyPI from GitHub Actions once trusted
publishing is configured.

## One-time setup

1. Create the `markdown-docx-compiler` project on PyPI if it does not already exist.
2. In PyPI, add a trusted publisher for this GitHub repository and the
   `.github/workflows/publish.yml` workflow.
3. In GitHub, create an environment named `pypi` if you want approval gates
   before the publish job runs.

## Pre-release checklist

Run the full validation suite locally:

```bash
uv sync
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/
uv build
uvx twine check dist/*
uv run python tests/compile_review_fixtures.py
```

Manual release gate:

- Import the generated DOCX fixtures into Google Docs and verify layout fidelity.
- Follow the visual checklist in `AGENTS.md` for headings, tables, code blocks,
  footer behavior, images, and CJK text.

## Publish a release

1. Bump `version` in `pyproject.toml`.
2. Update any user-facing docs or release notes that changed with the release.
3. Commit the release changes and merge them to `main`.
4. Create a Git tag and GitHub Release named `vX.Y.Z`.
5. GitHub Actions will run the `Publish` workflow and upload the built
   distributions to PyPI.

## Dry-run build

Use the `Publish` workflow via `workflow_dispatch` to build the wheel and sdist
and run `twine check` without uploading anything to PyPI.

## Post-release checks

- Confirm the README renders correctly on the PyPI project page.
- Install the released package in a clean environment and run `mdc --help`.
- Compile the sample fixture once from the published package.
