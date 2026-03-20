## Summary

Describe the user-facing or maintainer-facing change and why it is needed.

## Test plan

- [ ] `uv run ruff check src/ tests/`
- [ ] `uv run ruff format --check src/ tests/`
- [ ] `uv run mypy src/`
- [ ] `uv run pytest tests/`
- [ ] If DOCX output changed, ran `uv run python tests/compile_review_fixtures.py`

## Release notes

- [ ] No release note needed
- [ ] Update docs / help text
- [ ] Note breaking change

## Checklist

- [ ] Updated fixtures if compiler behavior changed
- [ ] Updated user-facing help text if behavior or config changed
- [ ] Included screenshots, rendered output notes, or reviewer guidance if visual output changed
