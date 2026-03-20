"""Parser and front matter tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from markdown_docx_compiler.models.document import (
    Blockquote,
    CodeBlock,
    Heading,
    Image,
    List,
    Paragraph,
    Table,
)
from markdown_docx_compiler.parser.front_matter import extract_front_matter
from markdown_docx_compiler.parser.markdown import parse_markdown


def test_extract_front_matter_and_body() -> None:
    raw = "---\ntitle: Demo\n---\n\n# Heading\n"

    metadata, body = extract_front_matter(raw)

    assert metadata["title"] == "Demo"
    assert body.strip() == "# Heading"


def test_invalid_front_matter_yaml_raises() -> None:
    raw = "---\ntitle: [unterminated\n---\n\n# Heading\n"

    with pytest.raises(ValueError, match="Invalid front matter YAML"):
        extract_front_matter(raw)


def test_front_matter_must_be_mapping() -> None:
    raw = "---\n- item\n---\n\n# Heading\n"

    with pytest.raises(ValueError, match="Front matter must be a mapping"):
        extract_front_matter(raw)


def test_parse_markdown_captures_anchor_and_blocks() -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample_report.md"
    metadata, body = extract_front_matter(fixture.read_text(encoding="utf-8"))
    document = parse_markdown(body, metadata=metadata, md_dir=str(fixture.parent))

    assert isinstance(document.body[0], Heading)
    assert isinstance(document.body[1], Paragraph)
    assert isinstance(document.body[2], Heading)
    assert isinstance(document.body[3], Table)
    assert document.body[3].meta.anchor == "results-table"
    assert document.body[3].column_count == 3
    assert isinstance(document.body[4], Heading)
    assert isinstance(document.body[5], List)
    assert isinstance(document.body[6], Blockquote)
    assert isinstance(document.body[7], CodeBlock)
    assert isinstance(document.body[8], Image)
    assert isinstance(document.body[9], Paragraph)


def test_parse_markdown_allows_anchor_on_top_level_list() -> None:
    document = parse_markdown("<!-- docx:id=task-list -->\n- Item one\n- Item two\n", metadata={})

    assert isinstance(document.body[0], List)
    assert document.body[0].meta.anchor == "task-list"


def test_nested_anchor_in_list_item_is_captured() -> None:
    markdown = "- <!-- docx:id=item-para -->\n  First item\n"
    document = parse_markdown(markdown, metadata={})

    block = document.body[0]
    assert isinstance(block, List)
    assert isinstance(block.items[0].blocks[0], Paragraph)
    assert block.items[0].blocks[0].meta.anchor == "item-para"


def test_region_tag_on_unsupported_block_type_is_rejected() -> None:
    markdown = "<!-- docx:page_footer.center -->\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"

    with pytest.raises(
        ValueError, match="Region tags only support top-level paragraphs, headings, and standalone images"
    ):
        parse_markdown(markdown, metadata={})


def test_region_tag_inside_list_item_is_rejected() -> None:
    markdown = "- <!-- docx:page_footer.center -->\n  First item\n"

    with pytest.raises(ValueError, match="Region tags are only supported on top-level paragraphs"):
        parse_markdown(markdown, metadata={})


def test_complex_blockquote_is_rejected() -> None:
    markdown = "> paragraph\n>\n> - nested item\n"

    with pytest.raises(ValueError, match="Blockquotes currently support paragraph content only"):
        parse_markdown(markdown, metadata={})
