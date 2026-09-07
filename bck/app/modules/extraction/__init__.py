"""Extraction module for Legal Metrology packaged commodity compliance.

Parses, normalises, and binds OCR text spans into statutory declaration fields.
"""

from app.modules.extraction.binder import ExtractionResult, bind_spans
from app.modules.extraction.category import propose_category

__all__ = [
    "ExtractionResult",
    "bind_spans",
    "propose_category",
]
