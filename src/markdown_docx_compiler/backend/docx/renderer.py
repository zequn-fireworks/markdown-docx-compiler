"""DOCX renderer for the compiler IR."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docx import Document
from docx.document import Document as DocxDocument
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.shared import Inches, Pt
from docx.text.run import Run

from markdown_docx_compiler.backend.docx.ooxml import (
    add_page_field,
    rgb,
    set_cell_shading,
    set_cell_vertical_alignment,
    set_cell_width,
    set_paragraph_bottom_border,
    set_paragraph_left_border,
    set_paragraph_shading,
    set_secondary_font,
    set_table_borders,
    set_table_cell_margins,
    set_table_grid,
    set_table_layout_fixed,
    set_table_width_dxa,
)
from markdown_docx_compiler.ir import (
    BlockNode,
    BlockQuoteBlock,
    CodeBlock,
    CodeSpan,
    Emphasis,
    HeadingBlock,
    HorizontalRuleBlock,
    ImageBlock,
    InlineNode,
    LineBreak,
    Link,
    ListBlock,
    ParagraphBlock,
    Strike,
    Strong,
    TableBlock,
    Text,
)
from markdown_docx_compiler.ir import (
    Document as IRDocument,
)
from markdown_docx_compiler.sidecar import BlockStyle, DocumentConfig
from markdown_docx_compiler.styles import Theme

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderContext:
    theme: Theme
    config: DocumentConfig

    @property
    def content_width_inches(self) -> float:
        total = self.config.page_width_inches or 8.5
        left = self.config.margin.left_inches or 1.0
        right = self.config.margin.right_inches or 1.0
        return total - left - right

    @property
    def content_width_twips(self) -> int:
        return int(self.content_width_inches * 1440)


class DocxRenderer:
    """Render typed IR into a Google-Docs-friendly DOCX."""

    def __init__(self, *, theme: Theme, config: DocumentConfig) -> None:
        self.context = RenderContext(theme=theme, config=config)
        self.document = Document()

    def render(self, ir_document: IRDocument, *, block_styles: dict[int, BlockStyle]) -> DocxDocument:
        self._configure_document()
        for block in ir_document.blocks:
            style = block_styles.get(block.meta.index, BlockStyle())
            self._render_block(block=block, style=style)
        return self.document

    def _configure_document(self) -> None:
        config = self.context.config
        for section in self.document.sections:
            section.top_margin = Inches(config.margin.top_inches or 1.0)
            section.bottom_margin = Inches(config.margin.bottom_inches or 0.8)
            section.left_margin = Inches(config.margin.left_inches or 1.0)
            section.right_margin = Inches(config.margin.right_inches or 1.0)
        normal = self.document.styles["Normal"]
        normal.font.name = config.font or "Aptos"
        normal.font.size = Pt(10.5)
        normal.font.color.rgb = rgb(config.text_color or "111827")
        self._setup_header()
        self._setup_footer()

    def _setup_header(self) -> None:
        logo_path = self.context.config.logo_path
        if not logo_path or not Path(logo_path).exists():
            return
        for section in self.document.sections:
            section.header_distance = Inches(0.3)
            header = section.header
            header.is_linked_to_previous = False
            paragraph = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = paragraph.add_run()
            run.add_picture(logo_path, width=Inches(0.7))

    def _setup_footer(self) -> None:
        footer_cfg = self.context.config.footer
        font = self.context.config.font or "Aptos"
        color = self.context.config.muted_color or "6B7280"
        for section in self.document.sections:
            footer = section.footer
            footer.is_linked_to_previous = False
            for paragraph in list(footer.paragraphs):
                paragraph.clear()
            paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
            paragraph.paragraph_format.space_before = Pt(8)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            content_width = self.context.content_width_twips
            p_pr = paragraph._p.get_or_add_pPr()
            border_color = self.context.config.border_color or "D1D5DB"
            p_pr.append(
                parse_xml(
                    f'<w:pBdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    f'  <w:top w:val="single" w:sz="4" w:space="4" w:color="{border_color}"/>'
                    f"</w:pBdr>"
                )
            )
            p_pr.append(
                parse_xml(
                    f'<w:tabs xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    f'  <w:tab w:val="center" w:pos="{content_width // 2}"/>'
                    f'  <w:tab w:val="right" w:pos="{content_width}"/>'
                    f"</w:tabs>"
                )
            )
            self._footer_run(paragraph, footer_cfg.left or "", font=font, color=color)
            self._footer_run(paragraph, "\t", font=font, color=color)
            self._footer_run(paragraph, footer_cfg.center or "", font=font, color=color)
            self._footer_run(paragraph, "\t", font=font, color=color)
            self._footer_run(paragraph, footer_cfg.right or "", font=font, color=color)
            if footer_cfg.show_page_numbers is not False:
                if footer_cfg.right:
                    self._footer_run(paragraph, " ", font=font, color=color)
                add_page_field(paragraph, font_name=font, font_size=8.0, color=color)

    def _footer_run(self, paragraph: Any, text: str, *, font: str, color: str) -> None:
        run = paragraph.add_run(text)
        run.font.name = font
        run.font.size = Pt(8.0)
        run.font.color.rgb = rgb(color)
        set_secondary_font(run, font)

    def _render_block(self, *, block: BlockNode, style: BlockStyle) -> None:
        if style.page_break_before:
            self.document.add_page_break()  # type: ignore[no-untyped-call]
        if isinstance(block, HeadingBlock):
            self._render_heading(block=block, style=style)
        elif isinstance(block, ParagraphBlock):
            self._render_paragraph(block=block, style=style)
        elif isinstance(block, ListBlock):
            self._render_list(block=block, style=style, level=0)
        elif isinstance(block, TableBlock):
            self._render_table(block=block, style=style)
        elif isinstance(block, CodeBlock):
            self._render_code_block(block=block, style=style)
        elif isinstance(block, BlockQuoteBlock):
            self._render_blockquote(block=block, style=style)
        elif isinstance(block, ImageBlock):
            self._render_image(block=block, style=style)
        elif isinstance(block, HorizontalRuleBlock):
            self._render_horizontal_rule()

    def _render_heading(self, *, block: HeadingBlock, style: BlockStyle) -> None:
        paragraph = self.document.add_paragraph()
        before = style.space_before if style.space_before is not None else self._heading_space_before(block.level)
        after = style.space_after if style.space_after is not None else self._heading_space_after(block.level)
        paragraph.paragraph_format.space_before = Pt(before)
        paragraph.paragraph_format.space_after = Pt(after)
        self._render_inline_nodes(
            paragraph=paragraph,
            nodes=block.content,
            font_size=style.font_size or self._heading_size(block.level),
            bold=True if style.bold is None else style.bold,
            italic=style.italic or False,
            color=style.color or self.context.config.primary_color or self.context.config.text_color or "111827",
        )

    def _render_paragraph(self, *, block: ParagraphBlock, style: BlockStyle) -> None:
        paragraph = self.document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(style.space_before or 0.0)
        paragraph.paragraph_format.space_after = Pt(style.space_after if style.space_after is not None else 6.0)
        paragraph.paragraph_format.line_spacing = style.line_spacing or 1.25
        self._render_inline_nodes(
            paragraph=paragraph, nodes=block.content, font_size=style.font_size, color=style.color
        )

    def _render_list(self, *, block: ListBlock, style: BlockStyle, level: int) -> None:
        for item in block.items:
            for inner in item.blocks:
                if isinstance(inner, ParagraphBlock):
                    paragraph = self.document.add_paragraph(style="List Number" if block.ordered else "List Bullet")
                    paragraph.paragraph_format.left_indent = Inches(0.35 * (level + 1))
                    paragraph.paragraph_format.space_before = Pt(style.space_before or 2.0)
                    paragraph.paragraph_format.space_after = Pt(style.space_after or 2.0)
                    self._render_inline_nodes(
                        paragraph=paragraph,
                        nodes=inner.content,
                        font_size=style.font_size,
                        color=style.color,
                    )
                elif isinstance(inner, ListBlock):
                    self._render_list(block=inner, style=style, level=level + 1)
                elif isinstance(inner, CodeBlock):
                    self._render_code_block(block=inner, style=style)

    def _render_table(self, *, block: TableBlock, style: BlockStyle) -> None:
        column_widths = self._table_column_widths(block=block, style=style)
        table = self.document.add_table(rows=1 + len(block.rows), cols=block.column_count)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_layout_fixed(table)
        set_table_width_dxa(table, sum(column_widths))
        set_table_grid(table, column_widths)
        set_table_borders(table, style.border_color or self.context.config.border_color or "D1D5DB")
        set_table_cell_margins(table)

        for col_idx, header in enumerate(block.headers):
            cell = table.rows[0].cells[col_idx]
            set_cell_width(cell, column_widths[col_idx])
            set_cell_vertical_alignment(cell)
            set_cell_shading(cell, style.background_color or "F3F4F6")
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_before = Pt(3)
            paragraph.paragraph_format.space_after = Pt(3)
            paragraph.alignment = self._alignment(block.alignments[col_idx])
            self._render_inline_nodes(
                paragraph=paragraph,
                nodes=header.content,
                font_size=style.font_size,
                bold=True,
                color=style.color,
            )

        for row_idx, row in enumerate(block.rows):
            for col_idx, cell_content in enumerate(row):
                cell = table.rows[row_idx + 1].cells[col_idx]
                set_cell_width(cell, column_widths[col_idx])
                set_cell_vertical_alignment(cell)
                paragraph = cell.paragraphs[0]
                paragraph.paragraph_format.space_before = Pt(2)
                paragraph.paragraph_format.space_after = Pt(2)
                align = block.alignments[col_idx] if col_idx < len(block.alignments) else "left"
                paragraph.alignment = self._alignment(align)
                self._render_inline_nodes(
                    paragraph=paragraph,
                    nodes=cell_content.content,
                    font_size=style.font_size,
                    color=style.color,
                )

    def _render_code_block(self, *, block: CodeBlock, style: BlockStyle) -> None:
        paragraph = self.document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(style.space_before or 6.0)
        paragraph.paragraph_format.space_after = Pt(style.space_after or 6.0)
        paragraph.paragraph_format.line_spacing = style.line_spacing or 1.15
        set_paragraph_shading(paragraph, style.background_color or "F3F4F6")
        run = paragraph.add_run(block.value)
        run.font.name = self.context.config.mono_font or "Consolas"
        run.font.size = Pt(style.font_size or 9.5)
        run.font.color.rgb = rgb(style.color or self.context.config.text_color or "111827")
        set_secondary_font(run, self.context.config.mono_font or "Consolas")

    def _render_blockquote(self, *, block: BlockQuoteBlock, style: BlockStyle) -> None:
        paragraph = self.document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(style.space_before or 8.0)
        paragraph.paragraph_format.space_after = Pt(style.space_after or 8.0)
        paragraph.paragraph_format.left_indent = Inches(0.3)
        set_paragraph_left_border(paragraph, style.border_color or self.context.config.primary_color or "94A3B8")
        self._render_inline_nodes(
            paragraph=paragraph,
            nodes=block.content,
            font_size=style.font_size,
            italic=True if style.italic is None else style.italic,
            color=style.color or self.context.config.muted_color or "6B7280",
        )

    def _render_image(self, *, block: ImageBlock, style: BlockStyle) -> None:
        paragraph = self.document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(style.space_before or 8.0)
        paragraph.paragraph_format.space_after = Pt(4 if block.alt_text else 8)
        run = paragraph.add_run()
        image_path = Path(block.path)
        if image_path.exists():
            run.add_picture(str(image_path), width=Inches(min(self.context.content_width_inches, 5.5)))
        else:
            logger.warning("Image not found, skipping: %s", image_path)
        if block.alt_text:
            caption = self.document.add_paragraph()
            caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
            caption.paragraph_format.space_after = Pt(8)
            caption_run = caption.add_run(block.alt_text)
            caption_run.font.name = self.context.config.font or "Aptos"
            caption_run.font.size = Pt(9.0)
            caption_run.font.color.rgb = rgb(self.context.config.muted_color or "6B7280")
            caption_run.italic = True
            set_secondary_font(caption_run, self.context.config.font or "Aptos")

    def _render_horizontal_rule(self) -> None:
        paragraph = self.document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(8)
        paragraph.paragraph_format.space_after = Pt(8)
        set_paragraph_bottom_border(paragraph, self.context.config.border_color or "D1D5DB")

    def _render_inline_nodes(
        self,
        *,
        paragraph: Any,
        nodes: Iterable[InlineNode],
        font_size: float | None = None,
        bold: bool = False,
        italic: bool = False,
        strike: bool = False,
        color: str | None = None,
    ) -> None:
        for node in nodes:
            self._render_inline_node(
                paragraph=paragraph,
                node=node,
                font_size=font_size,
                bold=bold,
                italic=italic,
                strike=strike,
                color=color,
            )

    def _render_inline_node(
        self,
        *,
        paragraph: Any,
        node: InlineNode,
        font_size: float | None,
        bold: bool,
        italic: bool,
        strike: bool,
        color: str | None,
    ) -> None:
        if isinstance(node, Text):
            run = paragraph.add_run(node.value)
            self._style_run(run=run, font_size=font_size, bold=bold, italic=italic, strike=strike, color=color)
            return
        if isinstance(node, LineBreak):
            paragraph.add_run().add_break()
            return
        if isinstance(node, Strong):
            self._render_inline_nodes(
                paragraph=paragraph,
                nodes=node.children,
                font_size=font_size,
                bold=True,
                italic=italic,
                strike=strike,
                color=color,
            )
            return
        if isinstance(node, Emphasis):
            self._render_inline_nodes(
                paragraph=paragraph,
                nodes=node.children,
                font_size=font_size,
                bold=bold,
                italic=True,
                strike=strike,
                color=color,
            )
            return
        if isinstance(node, Strike):
            self._render_inline_nodes(
                paragraph=paragraph,
                nodes=node.children,
                font_size=font_size,
                bold=bold,
                italic=italic,
                strike=True,
                color=color,
            )
            return
        if isinstance(node, CodeSpan):
            run = paragraph.add_run(node.value)
            run.font.name = self.context.config.mono_font or "Consolas"
            run.font.size = Pt(font_size or 9.5)
            run.font.color.rgb = rgb(color or self.context.config.text_color or "111827")
            set_secondary_font(run, self.context.config.mono_font or "Consolas")
            return
        if isinstance(node, Link):
            text = _stringify_inline(node.children)
            run = paragraph.add_run(text)
            run.underline = True
            self._style_run(
                run=run,
                font_size=font_size,
                bold=bold,
                italic=italic,
                strike=strike,
                color=color or self.context.config.primary_color or "2563EB",
            )

    def _style_run(
        self,
        *,
        run: Run,
        font_size: float | None,
        bold: bool,
        italic: bool,
        strike: bool,
        color: str | None,
    ) -> None:
        run.font.name = self.context.config.font or "Aptos"
        run.font.size = Pt(font_size or 10.5)
        run.font.color.rgb = rgb(color or self.context.config.text_color or "111827")
        run.bold = bold
        run.italic = italic
        run.font.strike = strike
        set_secondary_font(run, self.context.config.font or "Aptos")

    def _table_column_widths(self, *, block: TableBlock, style: BlockStyle) -> list[int]:
        total = self.context.content_width_twips
        if style.columns:
            return _parse_column_widths(style.columns, total=total, columns=block.column_count)
        return _auto_column_widths(block=block, total=total)

    def _heading_size(self, level: int) -> float:
        sizes = {1: 20.0, 2: 15.0, 3: 12.5, 4: 11.0, 5: 10.5, 6: 10.5}
        return sizes.get(level, 10.5)

    def _heading_space_before(self, level: int) -> float:
        spaces = {1: 28.0, 2: 22.0, 3: 16.0, 4: 12.0, 5: 10.0, 6: 10.0}
        return spaces.get(level, 10.0)

    def _heading_space_after(self, level: int) -> float:
        spaces = {1: 10.0, 2: 8.0, 3: 6.0, 4: 4.0, 5: 4.0, 6: 4.0}
        return spaces.get(level, 4.0)

    def _alignment(self, value: str) -> WD_ALIGN_PARAGRAPH:
        mapping = {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
        }
        return mapping.get(value, WD_ALIGN_PARAGRAPH.LEFT)


def _stringify_inline(nodes: Iterable[InlineNode]) -> str:
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, Text | CodeSpan):
            parts.append(node.value)
        elif isinstance(node, Link):
            parts.append(_stringify_inline(node.children))
        elif isinstance(node, LineBreak):
            parts.append("\n")
        elif isinstance(node, Strong | Emphasis | Strike):
            parts.append(_stringify_inline(node.children))
    return "".join(parts)


def _auto_column_widths(*, block: TableBlock, total: int) -> list[int]:
    max_lengths: list[int] = []
    for column_index in range(block.column_count):
        values = [_stringify_inline(block.headers[column_index].content)]
        for row in block.rows:
            if column_index < len(row):
                values.append(_stringify_inline(row[column_index].content))
        longest = max((len(_strip_markers(value)) for value in values), default=1)
        max_lengths.append(max(1, longest))
    combined = sum(max_lengths)
    raw_widths = [int(total * (value / combined)) for value in max_lengths]
    delta = total - sum(raw_widths)
    if raw_widths:
        raw_widths[-1] += delta
    return raw_widths


def _parse_column_widths(specs: list[str], *, total: int, columns: int) -> list[int]:
    if len(specs) < columns:
        specs = specs + ["1fr"] * (columns - len(specs))
    specs = specs[:columns]

    fractional_total = 0.0
    absolute_total = 0
    parsed: list[tuple[str, float | int]] = []
    for spec in specs:
        value = spec.strip().lower()
        if value.endswith("fr"):
            amount = float(value[:-2] or "1")
            parsed.append(("fr", amount))
            fractional_total += amount
        elif value.endswith("%"):
            amount = float(value[:-1]) / 100.0
            width = int(total * amount)
            parsed.append(("abs", width))
            absolute_total += width
        elif value.endswith("in"):
            amount = float(value[:-2])
            width = int(amount * 1440)
            parsed.append(("abs", width))
            absolute_total += width
        else:
            parsed.append(("fr", 1.0))
            fractional_total += 1.0

    remaining = max(total - absolute_total, 0)
    widths: list[int] = []
    for kind, amount in parsed:
        if kind == "abs":
            widths.append(int(amount))
        else:
            widths.append(int(remaining * (float(amount) / fractional_total)) if fractional_total else 0)
    delta = total - sum(widths)
    if widths:
        widths[-1] += delta
    return widths


def _strip_markers(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
