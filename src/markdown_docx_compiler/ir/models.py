"""Typed intermediate representation for markdown documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class BlockMeta:
    """Context captured for each parsed block."""

    anchor: str | None = None
    heading_path: tuple[str, ...] = ()
    index: int = 0


@dataclass(frozen=True)
class Text:
    value: str


@dataclass(frozen=True)
class LineBreak:
    hard: bool = False


@dataclass(frozen=True)
class Strong:
    children: list[InlineNode]


@dataclass(frozen=True)
class Emphasis:
    children: list[InlineNode]


@dataclass(frozen=True)
class Strike:
    children: list[InlineNode]


@dataclass(frozen=True)
class CodeSpan:
    value: str


@dataclass(frozen=True)
class Link:
    url: str
    children: list[InlineNode]


InlineNode = Text | LineBreak | Strong | Emphasis | Strike | CodeSpan | Link


@dataclass(frozen=True)
class HeadingBlock:
    level: int
    content: list[InlineNode]
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class ParagraphBlock:
    content: list[InlineNode]
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class HorizontalRuleBlock:
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class CodeBlock:
    value: str
    language: str | None = None
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class ImageBlock:
    path: str
    alt_text: str = ""
    title: str | None = None
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class BlockQuoteBlock:
    content: list[InlineNode]
    meta: BlockMeta = field(default_factory=BlockMeta)


@dataclass(frozen=True)
class TableCell:
    content: list[InlineNode]


@dataclass(frozen=True)
class TableBlock:
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
class ListBlock:
    ordered: bool
    items: list[ListItem]
    meta: BlockMeta = field(default_factory=BlockMeta)


BlockNode = (
    HeadingBlock
    | ParagraphBlock
    | HorizontalRuleBlock
    | CodeBlock
    | ImageBlock
    | BlockQuoteBlock
    | TableBlock
    | ListBlock
)


@dataclass(frozen=True)
class Document:
    metadata: dict[str, Any]
    blocks: list[BlockNode]
