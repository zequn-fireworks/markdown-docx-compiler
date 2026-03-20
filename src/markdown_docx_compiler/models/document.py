"""Typed intermediate representation for documents.

This module defines the complete document object model:
- Inline nodes (text spans with formatting)
- Block nodes (structural containers in the body)
- Region slots (content for page headers, footers, doc header)
- Document root (regions + body)
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Block metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BlockMeta:
    """Positional and tagging metadata attached to every block."""

    anchor: str | None = None
    index: int = 0


# ---------------------------------------------------------------------------
# Inline nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TextSpan:
    """Leaf text content."""

    text: str


@dataclass(frozen=True)
class LineBreak:
    hard: bool = False


@dataclass(frozen=True)
class StrongSpan:
    children: list[InlineNode]


@dataclass(frozen=True)
class EmphasisSpan:
    children: list[InlineNode]


@dataclass(frozen=True)
class StrikeSpan:
    children: list[InlineNode]


@dataclass(frozen=True)
class CodeSpan:
    text: str


@dataclass(frozen=True)
class LinkSpan:
    url: str
    children: list[InlineNode]


InlineNode = TextSpan | LineBreak | StrongSpan | EmphasisSpan | StrikeSpan | CodeSpan | LinkSpan


# ---------------------------------------------------------------------------
# Block nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Heading:
    level: int
    content: list[InlineNode]
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class Paragraph:
    content: list[InlineNode]
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class HorizontalRule:
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class CodeBlock:
    value: str
    language: str | None = None
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class Image:
    path: str
    alt_text: str = ""
    title: str | None = None
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class Blockquote:
    content: list[InlineNode]
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class TableCell:
    content: list[InlineNode]


@dataclass(frozen=True)
class Table:
    headers: list[TableCell]
    rows: list[list[TableCell]]
    alignments: list[Literal["left", "center", "right"]]
    meta: BlockMeta = field(default_factory=BlockMeta)

    @property
    def column_count(self) -> int:
        return len(self.headers)


@dataclass(frozen=True)
class ListItem:
    blocks: list[BlockNode]


@dataclass(frozen=True)
class List:
    ordered: bool
    items: list[ListItem]
    meta: BlockMeta = field(default_factory=BlockMeta)


BlockNode = Heading | Paragraph | HorizontalRule | CodeBlock | Image | Blockquote | Table | List

BLOCK_TYPE_NAMES: dict[type, str] = {
    Heading: "heading",
    Paragraph: "paragraph",
    HorizontalRule: "horizontal_rule",
    CodeBlock: "code",
    Image: "image",
    Blockquote: "blockquote",
    Table: "table",
    List: "list",
}


def block_type_name(block: BlockNode) -> str:
    return BLOCK_TYPE_NAMES.get(type(block), "unknown")


def walk_block_tree(blocks: list[BlockNode]) -> Iterator[BlockNode]:
    """Yield blocks in document order, including nested list-item blocks."""
    for block in blocks:
        yield block
        if isinstance(block, List):
            for item in block.items:
                yield from walk_block_tree(item.blocks)


# ---------------------------------------------------------------------------
# Region slots (page header / footer / doc header)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TextContent:
    """Rich text content for a region slot."""

    content: list[InlineNode]


@dataclass(frozen=True)
class ImageContent:
    """Image content for a region slot."""

    path: str
    alt_text: str = ""


SlotContent = TextContent | ImageContent

SlotItems = list[SlotContent]


@dataclass(frozen=True)
class Region:
    """A document region with left / center / right slots.

    Each slot holds an ordered list of content items (text and/or images)
    that are stacked vertically within the slot.
    """

    left: SlotItems = field(default_factory=list)
    center: SlotItems = field(default_factory=list)
    right: SlotItems = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.left and not self.center and not self.right


# ---------------------------------------------------------------------------
# Document root
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Document:
    """Complete parsed document."""

    metadata: dict[str, Any]
    page_header: Region = field(default_factory=Region)
    page_footer: Region = field(default_factory=Region)
    doc_header: Region = field(default_factory=Region)
    body: list[BlockNode] = field(default_factory=list)
