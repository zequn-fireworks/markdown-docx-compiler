"""Markdown parser front-end producing typed document IR."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdown_docx_compiler.ir import (
    BlockMeta,
    BlockNode,
    BlockQuoteBlock,
    CodeBlock,
    CodeSpan,
    Document,
    Emphasis,
    HeadingBlock,
    HorizontalRuleBlock,
    ImageBlock,
    InlineNode,
    LineBreak,
    Link,
    ListBlock,
    ListItem,
    ParagraphBlock,
    Strike,
    Strong,
    TableBlock,
    TableCell,
    Text,
)

HELP_TOPIC_MARKDOWN = """\
# Supported Markdown

## Block features

- headings (h1-h6)
- paragraphs
- ordered and bullet lists, including nesting
- fenced code blocks
- blockquotes
- horizontal rules
- tables (pipe syntax)
- standalone images via ![alt](path)

## Inline features

- **bold**
- *italic*
- ~~strikethrough~~
- `inline code`
- [links](url)
- hard and soft line breaks

## Not supported

These features are not handled by the compiler:

- arbitrary HTML (except docx: anchor comments)
- footnotes
- task lists (checkboxes)
- math / LaTeX
- custom inline directives
- definition lists
- nested blockquotes

The only recognized HTML is the anchor comment (see `mdc help anchors`):

  <!-- docx:id=name -->
"""

HELP_TOPIC_ANCHORS = """\
# Anchors

Anchors are optional HTML comments that tag specific blocks for styling
from the sidecar config.

## Syntax

  <!-- docx:id=name -->

## Rules

- The comment must be on its own line.
- It applies to the next markdown block.
- The comment itself is not rendered in the output.
- Only comments starting with docx: are treated as compiler metadata.

## Example

Markdown:

  <!-- docx:id=results-table -->
  | Model | TTFT | TPS |
  | --- | ---: | ---: |
  | A | 120 | 80 |

Sidecar:

  blocks:
    results-table:
      variant: benchmark
      columns: [3fr, 1fr, 1fr]

## When to use anchors

Prefer selectors for broad patterns (e.g. all tables under a heading).
Use anchors when you need to target one specific block that selectors
cannot distinguish by type, heading, or column count.
"""

_ANCHOR_RE = re.compile(r"<!--\s*docx:(.*?)-->")
_KV_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_-]*)=("[^"]*"|[^"\s]+)')


def parse_markdown(markdown_text: str, *, metadata: dict[str, Any], md_dir: str = ".") -> Document:
    """Parse markdown into the compiler IR."""
    md = MarkdownIt("commonmark", {"typographer": True}).enable(["table", "strikethrough"])
    tokens = md.parse(markdown_text)
    walker = _IRWalker(md_dir=md_dir)
    return Document(metadata=metadata, blocks=walker.walk(tokens))


class _IRWalker:
    def __init__(self, *, md_dir: str) -> None:
        self.md_dir = md_dir
        self.pending_anchor: dict[str, str] | None = None
        self.heading_path: list[str] = []
        self.block_index = 0

    def walk(self, tokens: list[Token]) -> list[BlockNode]:
        blocks: list[BlockNode] = []
        index = 0
        while index < len(tokens):
            token = tokens[index]

            if self._capture_anchor(token):
                index += 1
                continue

            if token.type == "heading_open":
                level = int(token.tag[1])
                inline = tokens[index + 1]
                content = _inline_from_token(inline)
                heading_text = inline.content.strip()
                self._update_heading_path(level=level, heading_text=heading_text)
                blocks.append(HeadingBlock(level=level, content=content, meta=self._next_meta()))
                index += 3
                continue

            if token.type == "paragraph_open":
                inline = tokens[index + 1]
                image = _image_from_inline(inline)
                if image is not None:
                    path, alt, title = image
                    blocks.append(
                        ImageBlock(
                            path=self._resolve_path(path),
                            alt_text=alt,
                            title=title,
                            meta=self._next_meta(),
                        )
                    )
                else:
                    blocks.append(ParagraphBlock(content=_inline_from_token(inline), meta=self._next_meta()))
                index += 3
                continue

            if token.type in {"bullet_list_open", "ordered_list_open"}:
                ordered = token.type == "ordered_list_open"
                close_type = "ordered_list_close" if ordered else "bullet_list_close"
                list_block, end_index = self._collect_list(tokens=tokens, start=index + 1, close_type=close_type)
                list_block = replace(list_block, meta=self._next_meta())
                blocks.append(list_block)
                index = end_index + 1
                continue

            if token.type == "table_open":
                table_block, end_index = self._collect_table(tokens=tokens, start=index + 1)
                blocks.append(replace(table_block, meta=self._next_meta()))
                index = end_index + 1
                continue

            if token.type == "fence":
                blocks.append(
                    CodeBlock(
                        value=token.content.rstrip("\n"),
                        language=token.info.strip() or None,
                        meta=self._next_meta(),
                    )
                )
                index += 1
                continue

            if token.type == "blockquote_open":
                quote, end_index = self._collect_blockquote(tokens=tokens, start=index + 1)
                blocks.append(BlockQuoteBlock(content=quote, meta=self._next_meta()))
                index = end_index + 1
                continue

            if token.type == "hr":
                blocks.append(HorizontalRuleBlock(meta=self._next_meta()))
                index += 1
                continue

            index += 1

        return blocks

    def _collect_list(self, *, tokens: list[Token], start: int, close_type: str) -> tuple[ListBlock, int]:
        items: list[ListItem] = []
        index = start
        ordered = close_type == "ordered_list_close"

        while index < len(tokens):
            token = tokens[index]
            if token.type == close_type:
                return ListBlock(ordered=ordered, items=items), index
            if token.type != "list_item_open":
                index += 1
                continue

            item_blocks: list[BlockNode] = []
            item_meta = self._next_meta()
            index += 1
            while index < len(tokens) and tokens[index].type != "list_item_close":
                token = tokens[index]
                if self._capture_anchor(token):
                    index += 1
                    continue
                if token.type == "paragraph_open":
                    inline = tokens[index + 1]
                    item_blocks.append(ParagraphBlock(content=_inline_from_token(inline), meta=item_meta))
                    index += 3
                    continue
                if token.type in {"bullet_list_open", "ordered_list_open"}:
                    nested_ordered = token.type == "ordered_list_open"
                    nested_close = "ordered_list_close" if nested_ordered else "bullet_list_close"
                    nested_list, index = self._collect_list(tokens=tokens, start=index + 1, close_type=nested_close)
                    item_blocks.append(replace(nested_list, meta=item_meta))
                    index += 1
                    continue
                if token.type == "fence":
                    item_blocks.append(
                        CodeBlock(value=token.content.rstrip("\n"), language=token.info.strip() or None, meta=item_meta)
                    )
                    index += 1
                    continue
                index += 1
            items.append(ListItem(blocks=item_blocks))
            index += 1

        return ListBlock(ordered=ordered, items=items), index

    def _collect_table(self, *, tokens: list[Token], start: int) -> tuple[TableBlock, int]:
        headers: list[TableCell] = []
        rows: list[list[TableCell]] = []
        alignments: list[Literal["left", "center", "right"]] = []
        current_row: list[TableCell] = []
        in_head = False
        in_body = False
        index = start
        while index < len(tokens):
            token = tokens[index]
            if token.type == "table_close":
                return TableBlock(headers=headers, rows=rows, alignments=alignments), index
            if token.type == "thead_open":
                in_head = True
            elif token.type == "thead_close":
                in_head = False
            elif token.type == "tbody_open":
                in_body = True
            elif token.type == "tbody_close":
                in_body = False
            elif token.type == "tr_open":
                current_row = []
            elif token.type == "tr_close":
                if in_head:
                    headers = current_row
                elif in_body:
                    rows.append(current_row)
            elif token.type in {"th_open", "td_open"}:
                if token.type == "th_open":
                    alignments.append(_alignment_from_attrs(token.attrs))
                inline = tokens[index + 1]
                current_row.append(TableCell(content=_inline_from_token(inline)))
                index += 2
            index += 1
        return TableBlock(headers=headers, rows=rows, alignments=alignments), index

    def _collect_blockquote(self, *, tokens: list[Token], start: int) -> tuple[list[InlineNode], int]:
        parts: list[InlineNode] = []
        index = start
        while index < len(tokens):
            token = tokens[index]
            if token.type == "blockquote_close":
                return parts, index
            if token.type == "inline":
                parts.extend(_inline_from_token(token))
            index += 1
        return parts, index

    def _update_heading_path(self, *, level: int, heading_text: str) -> None:
        while len(self.heading_path) >= level:
            self.heading_path.pop()
        self.heading_path.append(heading_text)

    def _next_meta(self) -> BlockMeta:
        self.block_index += 1
        anchor = None
        if self.pending_anchor:
            anchor = self.pending_anchor.get("id")
        self.pending_anchor = None
        return BlockMeta(anchor=anchor, heading_path=tuple(self.heading_path), index=self.block_index)

    def _capture_anchor(self, token: Token) -> bool:
        content = (token.content or "").strip()
        if token.type not in {"html_block", "html_inline"}:
            return False
        match = _ANCHOR_RE.fullmatch(content)
        if not match:
            return False
        self.pending_anchor = _parse_anchor_payload(match.group(1))
        return True

    def _resolve_path(self, path: str) -> str:
        p = Path(path)
        if p.is_absolute():
            return str(p)
        return str((Path(self.md_dir) / p).resolve())


def _inline_from_token(token: Token) -> list[InlineNode]:
    children = token.children or []
    parsed, _ = _inline_from_children(children=children, start=0, end_types=set())
    return parsed


def _inline_from_children(*, children: list[Token], start: int, end_types: set[str]) -> tuple[list[InlineNode], int]:
    items: list[InlineNode] = []
    index = start
    while index < len(children):
        child = children[index]
        if child.type in end_types:
            return items, index
        if child.type == "text":
            items.append(Text(child.content))
        elif child.type == "softbreak":
            items.append(LineBreak(hard=False))
        elif child.type == "hardbreak":
            items.append(LineBreak(hard=True))
        elif child.type == "code_inline":
            items.append(CodeSpan(child.content))
        elif child.type == "strong_open":
            nested, index = _inline_from_children(children=children, start=index + 1, end_types={"strong_close"})
            items.append(Strong(nested))
        elif child.type == "em_open":
            nested, index = _inline_from_children(children=children, start=index + 1, end_types={"em_close"})
            items.append(Emphasis(nested))
        elif child.type == "s_open":
            nested, index = _inline_from_children(children=children, start=index + 1, end_types={"s_close"})
            items.append(Strike(nested))
        elif child.type == "link_open":
            nested, index = _inline_from_children(children=children, start=index + 1, end_types={"link_close"})
            href = ""
            if child.attrs:
                href = str(child.attrs.get("href", ""))
            items.append(Link(url=href, children=nested))
        index += 1
    return items, index


def _image_from_inline(token: Token) -> tuple[str, str, str | None] | None:
    children = token.children or []
    non_empty = [
        child
        for child in children
        if child.type != "softbreak" and not (child.type == "text" and not child.content.strip())
    ]
    if len(non_empty) != 1 or non_empty[0].type != "image":
        return None
    image = non_empty[0]
    src = str(image.attrs.get("src", "")) if image.attrs else ""
    title_raw = image.attrs.get("title") if image.attrs else None
    title = str(title_raw) if title_raw is not None else None
    return src, image.content or "", title


def _alignment_from_attrs(attrs: dict[str, str | int | float] | None) -> Literal["left", "center", "right"]:
    style = str(attrs.get("style", "")) if attrs else ""
    if "right" in style:
        return "right"
    if "center" in style:
        return "center"
    return "left"


def _parse_anchor_payload(payload: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for key, raw_value in _KV_RE.findall(payload):
        data[key] = raw_value.strip('"')
    return data
