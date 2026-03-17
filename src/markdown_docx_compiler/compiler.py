"""Top-level compiler orchestration."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from markdown_docx_compiler.backend.docx import DocxRenderer
from markdown_docx_compiler.parser import extract_front_matter, parse_markdown
from markdown_docx_compiler.selectors import resolve_block_style, resolve_document_config
from markdown_docx_compiler.sidecar import DocumentConfig, load_sidecar

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompileResult:
    input_path: str
    output_path: str
    spec_path: str | None
    block_count: int
    theme: str
    dry_run: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compile_markdown_file(
    *,
    input_path: str | Path,
    output_path: str | Path | None = None,
    spec_path: str | Path | None = None,
    cli_overrides: DocumentConfig | None = None,
    template: str | None = None,
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
    theme, document_config, resolved_sidecar = resolve_document_config(
        front_matter=front_matter,
        sidecar=sidecar,
        cli_overrides=cli_overrides,
        template_override=template,
        base_dir=input_path.parent,
    )

    ir_document = parse_markdown(body, metadata=front_matter, md_dir=str(input_path.parent))
    block_styles = {
        block.meta.index: resolve_block_style(block=block, sidecar=resolved_sidecar, theme=theme)
        for block in ir_document.blocks
    }

    if not dry_run:
        renderer = DocxRenderer(theme=theme, config=document_config)
        document = renderer.render(ir_document, block_styles=block_styles)
        document.save(str(output_path))
        logger.debug("Wrote %s (%d blocks, theme=%s)", output_path, len(ir_document.blocks), theme.name)

    return CompileResult(
        input_path=str(input_path),
        output_path=str(output_path),
        spec_path=str(spec) if spec else None,
        block_count=len(ir_document.blocks),
        theme=theme.name,
        dry_run=dry_run,
    )


def discover_sidecar_path(input_path: Path) -> Path | None:
    """Discover sidecar next to the markdown file."""
    candidates = [
        input_path.with_suffix(".docx.yaml"),
        input_path.with_suffix(".docx.yml"),
        input_path.with_suffix(".docspec.yaml"),
        input_path.with_suffix(".docspec.yml"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _resolve_spec_path(*, input_path: Path, spec_path: str | Path | None) -> Path | None:
    if spec_path is None:
        return discover_sidecar_path(input_path)
    path = Path(spec_path)
    return path.resolve() if path.exists() or path.is_absolute() else (input_path.parent / path).resolve()
