"""Tests for block-level parsing into IR."""

from __future__ import annotations

from markdown_docx_compiler.ir import (
    BlockQuoteBlock,
    CodeBlock,
    HeadingBlock,
    HorizontalRuleBlock,
    ImageBlock,
    ListBlock,
    ParagraphBlock,
    TableBlock,
)
from markdown_docx_compiler.parser import extract_front_matter, parse_markdown


def _parse(md: str):
    meta, body = extract_front_matter(md)
    return parse_markdown(body, metadata=meta)


def test_heading_levels() -> None:
    doc = _parse("# H1\n\n## H2\n\n### H3\n")
    assert len(doc.blocks) == 3
    assert all(isinstance(b, HeadingBlock) for b in doc.blocks)
    assert [b.level for b in doc.blocks] == [1, 2, 3]


def test_paragraph() -> None:
    doc = _parse("Hello world.\n")
    assert len(doc.blocks) == 1
    assert isinstance(doc.blocks[0], ParagraphBlock)


def test_bullet_list() -> None:
    doc = _parse("- one\n- two\n- three\n")
    assert len(doc.blocks) == 1
    block = doc.blocks[0]
    assert isinstance(block, ListBlock)
    assert not block.ordered
    assert len(block.items) == 3


def test_ordered_list() -> None:
    doc = _parse("1. first\n2. second\n")
    assert len(doc.blocks) == 1
    block = doc.blocks[0]
    assert isinstance(block, ListBlock)
    assert block.ordered
    assert len(block.items) == 2


def test_nested_list() -> None:
    md = "- parent\n  - child\n  - child2\n- parent2\n"
    doc = _parse(md)
    assert len(doc.blocks) == 1
    block = doc.blocks[0]
    assert isinstance(block, ListBlock)
    assert len(block.items) == 2
    nested = [b for b in block.items[0].blocks if isinstance(b, ListBlock)]
    assert len(nested) == 1
    assert len(nested[0].items) == 2


def test_table() -> None:
    md = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n"
    doc = _parse(md)
    assert len(doc.blocks) == 1
    block = doc.blocks[0]
    assert isinstance(block, TableBlock)
    assert block.column_count == 2
    assert len(block.rows) == 2


def test_table_alignment() -> None:
    md = "| L | C | R |\n|:---|:---:|---:|\n| a | b | c |\n"
    doc = _parse(md)
    block = doc.blocks[0]
    assert isinstance(block, TableBlock)
    assert block.alignments == ["left", "center", "right"]


def test_code_block() -> None:
    md = "```python\nprint('hello')\n```\n"
    doc = _parse(md)
    assert len(doc.blocks) == 1
    block = doc.blocks[0]
    assert isinstance(block, CodeBlock)
    assert block.language == "python"
    assert "print" in block.value


def test_blockquote() -> None:
    doc = _parse("> This is a quote.\n")
    assert len(doc.blocks) == 1
    assert isinstance(doc.blocks[0], BlockQuoteBlock)


def test_horizontal_rule() -> None:
    doc = _parse("text above\n\n---\n\ntext below\n\n---\n")
    hr_blocks = [b for b in doc.blocks if isinstance(b, HorizontalRuleBlock)]
    assert len(hr_blocks) == 2


def test_image() -> None:
    doc = _parse("![alt text](image.png)\n")
    assert len(doc.blocks) == 1
    block = doc.blocks[0]
    assert isinstance(block, ImageBlock)
    assert block.alt_text == "alt text"
    assert "image.png" in block.path


def test_anchor_captured() -> None:
    md = "<!-- docx:id=my-table -->\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    doc = _parse(md)
    assert len(doc.blocks) == 1
    assert doc.blocks[0].meta.anchor == "my-table"


def test_front_matter_metadata() -> None:
    md = "---\ntitle: Test\ndate: 2026-01-01\n---\n\n# Hello\n"
    meta, body = extract_front_matter(md)
    assert meta["title"] == "Test"
    doc = parse_markdown(body, metadata=meta)
    assert doc.metadata["title"] == "Test"
