"""Sidecar loading and style resolution tests."""

from __future__ import annotations

from pathlib import Path

from markdown_docx_compiler.parser import extract_front_matter, parse_markdown
from markdown_docx_compiler.selectors import resolve_block_style, resolve_document_config
from markdown_docx_compiler.sidecar import load_sidecar


def test_sidecar_resolves_document_and_block_styles() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    markdown_path = fixture_dir / "sample_report.md"
    sidecar_path = fixture_dir / "sample_report.docx.yaml"

    metadata, body = extract_front_matter(markdown_path.read_text(encoding="utf-8"))
    sidecar = load_sidecar(sidecar_path)
    theme, document_config, resolved_sidecar = resolve_document_config(
        front_matter=metadata,
        sidecar=sidecar,
        cli_overrides=None,
        base_dir=fixture_dir,
    )
    document = parse_markdown(body, metadata=metadata, md_dir=str(fixture_dir))

    first_paragraph = document.blocks[1]
    results_table = document.blocks[3]
    paragraph_style = resolve_block_style(block=first_paragraph, sidecar=resolved_sidecar, theme=theme)
    table_style = resolve_block_style(block=results_table, sidecar=resolved_sidecar, theme=theme)

    assert theme.name == "fireworks"
    assert document_config.footer.left == "Fireworks AI  |  Confidential"
    assert document_config.footer.center == "2026-03-16"
    assert document_config.footer.right == "Draft"
    assert paragraph_style.variant == "lead"
    assert table_style.variant == "benchmark"
    assert table_style.columns == ["3fr", "1fr", "1fr"]
