"""Sidecar loading and style resolution tests."""

from __future__ import annotations

from pathlib import Path

from markdown_docx_compiler.models.document import TextContent
from markdown_docx_compiler.models.loader import load_sidecar
from markdown_docx_compiler.parser.front_matter import extract_front_matter
from markdown_docx_compiler.parser.markdown import parse_markdown
from markdown_docx_compiler.resolve.cascade import resolve_block_style, resolve_document_config


def test_sidecar_resolves_document_and_block_styles() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    markdown_path = fixture_dir / "sample_report.md"
    sidecar_path = fixture_dir / "sample_report.docx.yaml"

    metadata, body = extract_front_matter(markdown_path.read_text(encoding="utf-8"))
    sidecar = load_sidecar(sidecar_path)
    document_config = resolve_document_config(
        sidecar=sidecar,
        front_matter=metadata,
    )
    document = parse_markdown(body, metadata=metadata, md_dir=str(fixture_dir))

    assert document_config.font.family == "Aptos"

    assert len(document.page_footer.left) == 1
    assert isinstance(document.page_footer.left[0], TextContent)
    assert len(document.page_footer.center) == 1
    assert isinstance(document.page_footer.center[0], TextContent)
    assert len(document.page_footer.right) == 1
    assert isinstance(document.page_footer.right[0], TextContent)

    results_table = document.body[3]
    table_style = resolve_block_style(
        block=results_table,
        sidecar=sidecar,
        document=document_config,
    )
    assert table_style.table is not None
    assert table_style.table.columns == ["3fr", "1fr", "1fr"]
