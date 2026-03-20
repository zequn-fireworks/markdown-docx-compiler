"""End-to-end tests for the redesigned document pipeline."""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile

import pytest

from markdown_docx_compiler.compile import compile_markdown_file
from markdown_docx_compiler.models.config import BlockOverride, SidecarConfig
from markdown_docx_compiler.models.document import (
    Heading,
    ImageContent,
    Paragraph,
    Table,
    TextContent,
)
from markdown_docx_compiler.models.loader import load_sidecar
from markdown_docx_compiler.models.style import BlockStyle, FontStyle, SpacingStyle
from markdown_docx_compiler.parser.markdown import parse_markdown
from markdown_docx_compiler.resolve.cascade import (
    resolve_block_style,
    resolve_document_config,
    resolve_region_styles,
)
from markdown_docx_compiler.resolve.merge import merge_block_style

FIXTURE_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestBlockStyleMerge:
    def test_non_null_overrides(self) -> None:
        base = BlockStyle(font=FontStyle(size=12.0, color="111111"))
        override = BlockStyle(font=FontStyle(color="222222"))
        result = merge_block_style(base, override)
        assert result.font is not None
        assert result.font.size == 12.0
        assert result.font.color == "222222"

    def test_none_preserves_base(self) -> None:
        base = BlockStyle(spacing=SpacingStyle(before=8.0, after=4.0))
        override = BlockStyle()
        result = merge_block_style(base, override)
        assert result.spacing is not None
        assert result.spacing.before == 8.0

    def test_deep_nested_merge(self) -> None:
        base = BlockStyle(
            font=FontStyle(family="Arial", size=10.0),
            spacing=SpacingStyle(after=6.0),
        )
        override = BlockStyle(
            font=FontStyle(size=12.0),
            spacing=SpacingStyle(before=4.0),
        )
        result = merge_block_style(base, override)
        assert result.font is not None
        assert result.font.family == "Arial"
        assert result.font.size == 12.0
        assert result.spacing is not None
        assert result.spacing.after == 6.0
        assert result.spacing.before == 4.0


# ---------------------------------------------------------------------------
# Sidecar loading tests
# ---------------------------------------------------------------------------


class TestSidecarLoading:
    def test_load_sample_report(self) -> None:
        path = FIXTURE_DIR / "sample_report.docx.yaml"
        config = load_sidecar(path)
        assert isinstance(config, SidecarConfig)
        assert "paragraph" in config.defaults
        assert "results-table" in config.blocks

    def test_load_google_offer(self) -> None:
        path = Path(__file__).parent.parent / "examples" / "google-offer" / "offer.docx.yaml"
        config = load_sidecar(path)
        assert config.document.font.family == "Arial"
        assert config.page_header.image is not None
        assert config.page_header.image.width == "1.8in"
        assert "comp-table" in config.blocks
        assert config.blocks["comp-table"].type == "table"

    def test_load_missing_returns_defaults(self) -> None:
        config = load_sidecar(None)
        assert isinstance(config, SidecarConfig)
        assert config.defaults == {}


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestParser:
    def test_parse_basic_blocks(self) -> None:
        md = "# Title\n\nA paragraph.\n\n- Item one\n- Item two\n"
        doc = parse_markdown(md, metadata={})
        assert len(doc.body) == 3
        assert isinstance(doc.body[0], Heading)
        assert isinstance(doc.body[1], Paragraph)

    def test_parse_anchors(self) -> None:
        md = "<!-- docx:id=my-table -->\n| A | B |\n| - | - |\n| 1 | 2 |\n"
        doc = parse_markdown(md, metadata={})
        assert len(doc.body) == 1
        assert isinstance(doc.body[0], Table)
        assert doc.body[0].meta.anchor == "my-table"

    def test_parse_region_tags(self) -> None:
        md = (
            "<!-- docx:doc_header.left -->\n"
            "![Logo](logo.png)\n\n"
            "<!-- docx:page_footer.right -->\n"
            "{page}\n\n"
            "# Body\n\n"
            "Content here.\n"
        )
        doc = parse_markdown(md, metadata={})
        assert len(doc.doc_header.left) == 1
        assert isinstance(doc.doc_header.left[0], ImageContent)
        assert len(doc.page_footer.right) == 1
        assert isinstance(doc.page_footer.right[0], TextContent)
        assert len(doc.body) == 2
        assert isinstance(doc.body[0], Heading)

    def test_parse_region_multiple_items_per_slot(self) -> None:
        md = (
            "<!-- docx:doc_header.left -->\n"
            "![Logo](logo.png)\n\n"
            "<!-- docx:doc_header.left -->\n"
            "**Acme Corp**\n123 Main St\n\n"
            "<!-- docx:doc_header.right -->\n"
            "March 19, 2026\n\n"
            "<!-- docx:doc_header.right -->\n"
            "John Doe\n456 Oak Ave\n\n"
            "Body paragraph.\n"
        )
        doc = parse_markdown(md, metadata={})
        assert len(doc.doc_header.left) == 2
        assert isinstance(doc.doc_header.left[0], ImageContent)
        assert isinstance(doc.doc_header.left[1], TextContent)
        assert len(doc.doc_header.right) == 2
        assert isinstance(doc.doc_header.right[0], TextContent)
        assert isinstance(doc.doc_header.right[1], TextContent)
        assert len(doc.body) == 1

    def test_parse_table(self) -> None:
        md = "| X | Y |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |\n"
        doc = parse_markdown(md, metadata={})
        assert len(doc.body) == 1
        table = doc.body[0]
        assert isinstance(table, Table)
        assert table.column_count == 2
        assert len(table.rows) == 2


# ---------------------------------------------------------------------------
# Cascade tests
# ---------------------------------------------------------------------------


class TestCascade:
    def test_document_config_resolution(self) -> None:
        sidecar = load_sidecar(FIXTURE_DIR / "sample_report.docx.yaml")
        config = resolve_document_config(sidecar=sidecar)
        assert config.font.family == "Aptos"
        assert config.font.size == 10.5

    def test_block_style_with_anchor(self) -> None:
        sidecar = load_sidecar(FIXTURE_DIR / "sample_report.docx.yaml")
        config = resolve_document_config(sidecar=sidecar)
        md = "<!-- docx:id=results-table -->\n| A | B | C |\n| - | - | - |\n| 1 | 2 | 3 |\n"
        doc = parse_markdown(md, metadata={})
        table = doc.body[0]
        style = resolve_block_style(block=table, sidecar=sidecar, document=config)
        assert style.table is not None
        assert style.table.columns == ["3fr", "1fr", "1fr"]

    def test_block_override_type_mismatch_raises(self) -> None:
        sidecar = SidecarConfig(
            blocks={
                "results-table": BlockOverride(type="paragraph", style=BlockStyle()),
            }
        )
        config = resolve_document_config(sidecar=sidecar)
        md = "<!-- docx:id=results-table -->\n| A | B |\n| - | - |\n| 1 | 2 |\n"
        doc = parse_markdown(md, metadata={})

        with pytest.raises(ValueError, match="Block override type mismatch"):
            resolve_block_style(block=doc.body[0], sidecar=sidecar, document=config)

    def test_region_style_resolution(self) -> None:
        sidecar = load_sidecar(FIXTURE_DIR / "sample_report.docx.yaml")
        _, page_footer, _ = resolve_region_styles(sidecar)
        assert page_footer.font is not None
        assert page_footer.font.size == 8.0


# ---------------------------------------------------------------------------
# End-to-end compilation tests
# ---------------------------------------------------------------------------


class TestCompilation:
    def test_sample_report(self, tmp_path: Path) -> None:
        output = tmp_path / "sample_report.docx"
        result = compile_markdown_file(
            input_path=FIXTURE_DIR / "sample_report.md",
            output_path=output,
        )
        assert result.block_count == 10
        assert output.exists()

        with ZipFile(output) as z:
            doc_xml = z.read("word/document.xml").decode()
        assert 'w:tblLayout w:type="fixed"' in doc_xml
        assert "<w:gridCol" in doc_xml

    def test_showcase_en(self, tmp_path: Path) -> None:
        output = tmp_path / "showcase_en.docx"
        result = compile_markdown_file(
            input_path=FIXTURE_DIR / "showcase_en.md",
            output_path=output,
        )
        assert result.block_count > 0
        assert output.exists()

    def test_showcase_zh(self, tmp_path: Path) -> None:
        output = tmp_path / "showcase_zh.docx"
        result = compile_markdown_file(
            input_path=FIXTURE_DIR / "showcase_zh.md",
            output_path=output,
        )
        assert result.block_count > 0
        assert output.exists()

    def test_google_offer(self, tmp_path: Path) -> None:
        offer_dir = Path(__file__).parent.parent / "examples" / "google-offer"
        output = tmp_path / "offer.docx"
        result = compile_markdown_file(
            input_path=offer_dir / "offer.md",
            output_path=output,
        )
        assert result.block_count > 0
        assert output.exists()

    def test_dry_run(self) -> None:
        result = compile_markdown_file(
            input_path=FIXTURE_DIR / "sample_report.md",
            output_path=None,
            dry_run=True,
        )
        assert result.dry_run is True
        assert result.block_count == 10

    def test_table_column_widths_in_docx(self, tmp_path: Path) -> None:
        output = tmp_path / "sample.docx"
        compile_markdown_file(
            input_path=FIXTURE_DIR / "sample_report.md",
            output_path=output,
        )
        with ZipFile(output) as z:
            doc_xml = z.read("word/document.xml").decode()
        widths = [int(v) for v in re.findall(r'w:gridCol w:w="(\d+)"', doc_xml)]
        assert len(widths) >= 3
        assert widths[0] > widths[1]

    def test_image_embedded(self, tmp_path: Path) -> None:
        output = tmp_path / "sample.docx"
        compile_markdown_file(
            input_path=FIXTURE_DIR / "sample_report.md",
            output_path=output,
        )
        with ZipFile(output) as z:
            media = {n for n in z.namelist() if n.startswith("word/media/")}
        assert media

    def test_links_are_emitted_as_real_hyperlinks_and_title_metadata(self, tmp_path: Path) -> None:
        markdown = tmp_path / "linked.md"
        markdown.write_text(
            "---\ntitle: Linked Document\n---\n\n[Example](https://example.com)\n",
            encoding="utf-8",
        )
        output = tmp_path / "linked.docx"

        compile_markdown_file(input_path=markdown, output_path=output)

        with ZipFile(output) as z:
            document_xml = z.read("word/document.xml").decode()
            relationships = z.read("word/_rels/document.xml.rels").decode()
            core_props = z.read("docProps/core.xml").decode()

        assert "w:hyperlink" in document_xml
        assert "https://example.com" in relationships
        assert "Linked Document" in core_props
