"""Parser and front matter tests."""

from __future__ import annotations

from pathlib import Path

from markdown_docx_compiler.ir import (
    BlockQuoteBlock,
    CodeBlock,
    HeadingBlock,
    ImageBlock,
    ListBlock,
    ParagraphBlock,
    TableBlock,
)
from markdown_docx_compiler.parser import extract_front_matter, parse_markdown


def test_extract_front_matter_and_body() -> None:
    raw = "---\ntitle: Demo\n---\n\n# Heading\n"

    metadata, body = extract_front_matter(raw)

    assert metadata["title"] == "Demo"
    assert body.strip() == "# Heading"


def test_parse_markdown_captures_anchor_and_blocks() -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample_report.md"
    metadata, body = extract_front_matter(fixture.read_text(encoding="utf-8"))
    document = parse_markdown(body, metadata=metadata, md_dir=str(fixture.parent))

    assert isinstance(document.blocks[0], HeadingBlock)
    assert isinstance(document.blocks[1], ParagraphBlock)
    assert isinstance(document.blocks[2], HeadingBlock)
    assert isinstance(document.blocks[3], TableBlock)
    assert document.blocks[3].meta.anchor == "results-table"
    assert document.blocks[3].column_count == 3
    assert isinstance(document.blocks[4], HeadingBlock)
    assert isinstance(document.blocks[5], ListBlock)
    assert isinstance(document.blocks[6], BlockQuoteBlock)
    assert isinstance(document.blocks[7], CodeBlock)
    assert isinstance(document.blocks[8], ImageBlock)
    assert isinstance(document.blocks[9], ParagraphBlock)
