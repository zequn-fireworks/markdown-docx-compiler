"""Front matter helpers."""

from __future__ import annotations

import re
from typing import Any

import yaml

HELP_TOPIC = """\
# Front Matter

Use YAML front matter for document-level metadata.  Front matter overrides
theme defaults but is itself overridden by sidecar config and CLI flags.

## Example

  ---
  title: Benchmark Report
  template: fireworks-rca
  footer_center: 2026-03-16
  logo_path: ./figures/logo.png
  ---

## Supported keys

  title                str    Document title
  template             str    Template name (e.g. "fireworks-rca")
  logo_path            str    Path to logo image (relative to markdown file)
  font                 str    Body font name
  mono_font            str    Monospace font name
  primary_color        str    Hex color without # (e.g. "6720FF")
  text_color           str    Hex color for body text
  muted_color          str    Hex color for secondary text
  border_color         str    Hex color for borders
  page_width_inches    float  Page width in inches (default 8.5)
  footer_left          str    Footer left text
  footer_center        str    Footer center text
  footer_right         str    Footer right text
  margin_top_inches    float  Top margin in inches
  margin_bottom_inches float  Bottom margin in inches
  margin_left_inches   float  Left margin in inches
  margin_right_inches  float  Right margin in inches
"""

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.+?)\n---\s*\n", re.DOTALL)


def extract_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Return front matter and remaining markdown body."""
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, text[match.end() :]
