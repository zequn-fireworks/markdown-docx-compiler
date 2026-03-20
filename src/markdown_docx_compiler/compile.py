"""Top-level compiler orchestration (new pipeline).

This replaces the old ``compiler.py`` and uses the redesigned models,
parser, cascade, and renderer.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from markdown_docx_compiler.backend.docx.doc_renderer import DocxRenderer
from markdown_docx_compiler.models.loader import load_sidecar
from markdown_docx_compiler.parser.front_matter import extract_front_matter
from markdown_docx_compiler.parser.markdown import parse_markdown
from markdown_docx_compiler.resolve.cascade import (
    resolve_all_block_styles,
    resolve_document_config,
    resolve_region_styles,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompileResult:
    input_path: str
    output_path: str
    spec_path: str | None
    block_count: int
    dry_run: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compile_markdown_file(
    *,
    input_path: str | Path,
    output_path: str | Path | None = None,
    spec_path: str | Path | None = None,
    dry_run: bool = False,
) -> CompileResult:
    """Compile a markdown file into a styled DOCX."""
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if output_path is None:
        output_path = input_path.with_suffix(".docx")
    output_path = Path(output_path).resolve()

    spec = _resolve_spec_path(input_path=input_path, spec_path=spec_path)

    logger.debug("Compiling %s -> %s (spec=%s)", input_path, output_path, spec)

    raw_text = input_path.read_text(encoding="utf-8")
    front_matter, body = extract_front_matter(raw_text)

    sidecar = load_sidecar(spec)

    document_config = resolve_document_config(
        sidecar=sidecar,
        front_matter=front_matter,
    )

    ir_document = parse_markdown(body, metadata=front_matter, md_dir=str(input_path.parent))

    block_styles = resolve_all_block_styles(
        blocks=ir_document.body,
        sidecar=sidecar,
        document=document_config,
    )

    page_header_style, page_footer_style, doc_header_style = resolve_region_styles(sidecar)

    if not dry_run:
        renderer = DocxRenderer(
            config=document_config,
            page_header_style=page_header_style,
            page_footer_style=page_footer_style,
            doc_header_style=doc_header_style,
        )
        docx_document = renderer.render(ir_document, block_styles=block_styles)
        docx_document.save(str(output_path))
        logger.debug("Wrote %s (%d blocks)", output_path, len(ir_document.body))

    return CompileResult(
        input_path=str(input_path),
        output_path=str(output_path),
        spec_path=str(spec) if spec else None,
        block_count=len(ir_document.body),
        dry_run=dry_run,
    )


def discover_sidecar_path(input_path: Path) -> Path | None:
    """Discover sidecar next to the markdown file."""
    candidate = input_path.with_suffix(".docx.yaml")
    if candidate.exists():
        return candidate
    return None


def _resolve_spec_path(*, input_path: Path, spec_path: str | Path | None) -> Path | None:
    if spec_path is None:
        return discover_sidecar_path(input_path)
    return Path(spec_path).resolve()
