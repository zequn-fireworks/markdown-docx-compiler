"""Discovery payload builder for agent self-exploration."""

from __future__ import annotations

import dataclasses
from typing import Any

from markdown_docx_compiler import __version__


def build_discovery_payload() -> dict[str, Any]:
    """Build the machine-readable discovery payload returned by ``mdc --json``."""
    from markdown_docx_compiler.models.style import BlockStyle
    from markdown_docx_compiler.styles.themes import DEFAULT_THEME

    doc = DEFAULT_THEME.document
    default_brand: dict[str, Any] = {
        "font": doc.font,
        "mono_font": doc.mono_font,
        "primary_color": doc.primary_color,
        "text_color": doc.text_color,
        "muted_color": doc.muted_color,
        "border_color": doc.border_color,
    }
    if DEFAULT_THEME.variants:
        default_brand["variants"] = {
            block_type: list(variants.keys()) for block_type, variants in DEFAULT_THEME.variants.items()
        }

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
            "template": {
                "aliases": ["tpl"],
                "description": "Browse installable template packages",
                "verbs": {
                    "list": {"description": "List installed templates"},
                    "show": {
                        "description": "Show template details",
                        "args": {"name": "Template name"},
                    },
                },
            },
            "theme": {
                "aliases": [],
                "description": "Browse built-in themes and variants",
                "verbs": {
                    "list": {"description": "List themes and variants"},
                    "show": {
                        "description": "Show theme details",
                        "args": {"name?": "Theme name (default: default)"},
                    },
                },
            },
        },
        "reference": {
            "sidecar_autodiscovery": [
                "<name>.docx.yaml",
                "<name>.docx.yml",
                "<name>.docspec.yaml",
                "<name>.docspec.yml",
            ],
            "anchor_syntax": "<!-- docx:id=name -->",
            "default_brand": default_brand,
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
                "built-in defaults (fonts, colors, margins)",
                "sidecar document globals + type defaults",
                "sidecar block instance overrides (by anchor)",
                "front matter overrides",
            ],
        },
        "hint": "Run `mdc <noun> --help` for detailed reference documentation.",
    }
