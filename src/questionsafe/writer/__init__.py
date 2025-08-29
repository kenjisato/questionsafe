# src/questionsafe/writer/__init__.py
# Public API is provided by the Moodle backend.
from .moodle import render_xml, render_html, write_xml, write_html

__all__ = ["render_xml", "render_html", "write_xml", "write_html"]
