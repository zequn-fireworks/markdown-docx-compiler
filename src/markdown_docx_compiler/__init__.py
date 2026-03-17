"""Public API for markdown-docx-compiler."""

from importlib.metadata import version

from .compiler import CompileResult, compile_markdown_file, discover_sidecar_path

__all__ = ["HELP_TOPIC", "CompileResult", "__version__", "compile_markdown_file", "discover_sidecar_path"]

__version__: str = version("markdown-docx-compiler")

HELP_TOPIC = """\
# markdown-docx-compiler

Compile AI-authored markdown into polished .docx for Google Docs import.

## Quick start

  mdc document create report.md -o report.docx
  mdc doc create report.md --spec report.docx.yaml -o report.docx
  mdc document validate report.md

## Reference documentation

  mdc document --help    Supported markdown features and anchors
  mdc spec --help        Sidecar config structure and selectors
  mdc template --help    Installable template packages and usage
  mdc theme --help       Built-in brand, variants, and customization

## Explore

  mdc --json             Machine-readable discovery payload (all nouns/verbs)
  mdc template list      List installed templates
  mdc theme list         List available themes
  mdc spec show --for report.md --resolved   Show fully merged config

Use --json with any command for machine-readable output.
"""
