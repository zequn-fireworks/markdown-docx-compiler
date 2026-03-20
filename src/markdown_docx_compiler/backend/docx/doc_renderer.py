"""Top-level DOCX renderer: Document IR + resolved styles -> python-docx."""

from __future__ import annotations

from docx import Document as NewDocxDocument
from docx.document import Document as DocxDocumentType
from docx.shared import Inches, Pt

from markdown_docx_compiler.backend.docx.blocks import render_block
from markdown_docx_compiler.backend.docx.ooxml_helpers import rgb
from markdown_docx_compiler.backend.docx.regions import (
    render_doc_header,
    render_page_footer,
    render_page_header,
)
from markdown_docx_compiler.models.config import DocumentConfig, RegionStyle
from markdown_docx_compiler.models.document import Document as IRDocument
from markdown_docx_compiler.models.style import BlockStyle
from markdown_docx_compiler.resolve.defaults import DEFAULT_DOCUMENT


class DocxRenderer:
    """Render a full ``Document`` IR into a Google-Docs-friendly DOCX.

    Accepts the resolved ``DocumentConfig`` plus per-region styles produced
    by the cascade, then drives the DOCX generation through page setup,
    region rendering, and block dispatch.
    """

    def __init__(
        self,
        *,
        config: DocumentConfig,
        page_header_style: RegionStyle,
        page_footer_style: RegionStyle,
        doc_header_style: RegionStyle,
    ) -> None:
        self.config = config
        self.page_header_style = page_header_style
        self.page_footer_style = page_footer_style
        self.doc_header_style = doc_header_style
        self.document = NewDocxDocument()

    def render(
        self,
        ir: IRDocument,
        *,
        block_styles: dict[int, BlockStyle],
    ) -> DocxDocumentType:
        """Build a complete python-docx document from the IR and resolved styles."""
        self._configure_document()

        render_page_header(
            doc=self.document,
            region=ir.page_header,
            style=self.page_header_style,
            config=self.config,
        )
        render_page_footer(
            doc=self.document,
            region=ir.page_footer,
            style=self.page_footer_style,
            config=self.config,
        )
        render_doc_header(
            doc=self.document,
            region=ir.doc_header,
            style=self.doc_header_style,
            config=self.config,
        )

        cw_inches = self._content_width_inches
        cw_twips = self._content_width_twips

        for block in ir.body:
            style = block_styles.get(block.meta.index, BlockStyle())
            render_block(
                doc=self.document,
                block=block,
                style=style,
                block_styles=block_styles,
                config=self.config,
                content_width_inches=cw_inches,
                content_width_twips=cw_twips,
            )

        return self.document

    # -- Document setup ----------------------------------------------------

    def _configure_document(self) -> None:
        config = self.config
        page = config.page
        _d = DEFAULT_DOCUMENT
        if config.title:
            self.document.core_properties.title = config.title
        for section in self.document.sections:
            section.top_margin = Inches(page.margin.top or _d.page.margin.top or 1.0)
            section.bottom_margin = Inches(page.margin.bottom or _d.page.margin.bottom or 0.8)
            section.left_margin = Inches(page.margin.left or _d.page.margin.left or 1.0)
            section.right_margin = Inches(page.margin.right or _d.page.margin.right or 1.0)

        normal = self.document.styles["Normal"]
        normal.font.name = config.font.family or _d.font.family or "Aptos"
        normal.font.size = Pt(config.font.size or _d.font.size or 10.5)
        normal.font.color.rgb = rgb(config.font.color or _d.font.color or "111827")

    @property
    def _content_width_inches(self) -> float:
        _d = DEFAULT_DOCUMENT
        total = self.config.page.width_inches or _d.page.width_inches or 8.5
        left = self.config.page.margin.left or _d.page.margin.left or 1.0
        right = self.config.page.margin.right or _d.page.margin.right or 1.0
        return total - left - right

    @property
    def _content_width_twips(self) -> int:
        return int(self._content_width_inches * 1440)
