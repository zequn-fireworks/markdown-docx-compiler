"""Discovery payload builder for agent self-exploration."""

from __future__ import annotations

import dataclasses
from typing import Any

from markdown_docx_compiler import __version__


def build_discovery_payload() -> dict[str, Any]:
    """Build the machine-readable discovery payload returned by ``mdc --json``."""
    from markdown_docx_compiler.models.style import BlockStyle
    from markdown_docx_compiler.resolve.defaults import DEFAULT_DOCUMENT

    document_defaults = dataclasses.asdict(DEFAULT_DOCUMENT)

    return {
        "version": __version__,
        "nouns": {
            "document": {
                "aliases": ["doc"],
                "description": "Compile and validate markdown documents",
                "verbs": {
                    "create": {
                        "description": "Compile markdown into styled DOCX",
                        "args": {"input": "Markdown file path"},
                        "flags": {
                            "--output-file/-o": "Output DOCX path",
                            "--spec": "Sidecar YAML path",
                        },
                    },
                    "validate": {
                        "description": "Parse and resolve without writing the DOCX",
                        "args": {"input": "Markdown file path"},
                        "flags": {
                            "--spec": "Sidecar YAML path",
                        },
                    },
                },
            },
            "spec": {
                "aliases": [],
                "description": "Manage sidecar configuration files",
                "verbs": {
                    "show": {
                        "description": "Display sidecar content or resolved config",
                        "args": {"path?": "Sidecar YAML path (optional if --for is used)"},
                        "flags": {
                            "--for": "Discover sidecar for this markdown file",
                            "--resolved": "Show fully merged config",
                        },
                    },
                    "validate": {
                        "description": "Check sidecar YAML validity",
                        "args": {"path?": "Sidecar YAML path (optional if --for is used)"},
                        "flags": {"--for": "Discover sidecar for this markdown file"},
                    },
                    "create": {
                        "description": "Scaffold a new sidecar YAML",
                        "args": {"path?": "Output file path (default: stdout)"},
                    },
                },
            },
        },
        "reference": {
            "sidecar_autodiscovery": ["<name>.docx.yaml"],
            "anchor_syntax": "<!-- docx:id=name -->",
            "builtin_document_defaults": document_defaults,
            "block_types": [
                "paragraph",
                "table",
                "code",
                "blockquote",
                "list",
                "image",
                "heading",
                "horizontal_rule",
            ],
            "front_matter_keys": {
                "title": "str",
                "font": "str",
                "mono_font": "str",
                "text_color": "str",
                "link_color": "str",
                "page_width_inches": "float",
                "margin_top": "float",
                "margin_bottom": "float",
                "margin_left": "float",
                "margin_right": "float",
            },
            "block_style_properties": [f.name for f in dataclasses.fields(BlockStyle)],
            "resolution_order": [
                "built-in document + block defaults",
                "sidecar document globals + type defaults",
                "sidecar block instance overrides (by anchor)",
                "front matter overrides document config",
            ],
        },
        "hint": "Run `mdc <noun> --help` for detailed reference documentation.",
    }
