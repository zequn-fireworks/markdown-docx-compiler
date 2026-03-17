"""Compile fixture markdown files for manual review."""

from __future__ import annotations

import json
from pathlib import Path

from markdown_docx_compiler import compile_markdown_file


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fixture_dir = repo_root / "tests" / "fixtures"
    output_dir = repo_root / "tests" / "manual_review_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown_files = sorted(path for path in fixture_dir.glob("*.md") if path.is_file())
    results = []
    for markdown_path in markdown_files:
        output_path = output_dir / f"{markdown_path.stem}.docx"
        result = compile_markdown_file(input_path=markdown_path, output_path=output_path)
        results.append(result.to_dict())

    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
