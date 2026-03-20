# Releasing `markdown-docx-compiler`

This repository is set up to publish to PyPI from GitHub Actions once trusted
publishing is configured.

## One-time setup

1. Create the `markdown-docx-compiler` project on PyPI if it does not already exist.
2. In PyPI, add a trusted publisher for this GitHub repository and the
   `.github/workflows/publish.yml` workflow.
3. Optionally create the same project on TestPyPI if you want a full rehearsal
   before the first real release.
4. In GitHub, create an environment named `pypi` if you want approval gates
   before the publish job runs.

## Dry-run build

Use the `Publish` workflow via `workflow_dispatch` to build the wheel and sdist
and run `twine check` without uploading anything to PyPI.

This is the fastest way to validate the packaging path in CI before a real
release.

## TestPyPI rehearsal

Before the first real release, do one full rehearsal against TestPyPI.

1. Run the full local validation suite:

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

2. Trigger the `Publish` workflow with `workflow_dispatch` and confirm the
   build artifacts and `twine check` results look correct.
3. Upload the built `dist/*` artifacts to TestPyPI using your preferred secure
   method.
4. In a clean environment, verify the TestPyPI package install and CLI:

```bash
pip install --index-url https://test.pypi.org/simple/ markdown-docx-compiler
mdc --help
```

If you use CLI-isolated environments, also verify:

```bash
pipx install --index-url https://test.pypi.org/simple/ markdown-docx-compiler
uv tool install --index-url https://test.pypi.org/simple/ markdown-docx-compiler
```

5. Compile one example document from the installed package.

## Per-release checklist

Run the same validation suite locally before every release:

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

Update release-facing materials:

- Bump `version` in `pyproject.toml`.
- Update `CHANGELOG.md`.
- Update any user-facing docs or examples that changed with the release.

## Publish a real release

1. Merge the release-ready changes to `main`.
2. Create a Git tag and GitHub Release named `vX.Y.Z`.
3. Publishing the GitHub Release triggers `.github/workflows/publish.yml`.
4. GitHub Actions builds the wheel and sdist, validates them with `twine
   check`, and uploads them to PyPI through trusted publishing.

## Post-release checks

- Confirm the README renders correctly on the PyPI project page.
- Install the released package in a clean environment and run `mdc --help`.
- Verify the CLI install flows:

```bash
pip install markdown-docx-compiler
pipx install markdown-docx-compiler
uv tool install markdown-docx-compiler
mdc --help
```

- Compile one example document from the published package:

```bash
mdc doc create examples/goggle-offer/offer.md
```

- Confirm the package metadata on PyPI links to the repository, examples, and
  changelog as expected.
