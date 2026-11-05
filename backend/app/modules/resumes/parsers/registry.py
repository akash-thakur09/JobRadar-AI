"""Parser registry and dynamic selector."""

from app.modules.resumes.parsers.base import BaseResumeParser
from app.modules.resumes.parsers.docx import DocxParser
from app.modules.resumes.parsers.pdf import PdfParser

_PARSERS: list[BaseResumeParser] = [
    PdfParser(),
    DocxParser(),
]


def get_parser_for_mime_type(mime_type: str, filename: str) -> BaseResumeParser:
    """Return the matching parser for the uploaded file format."""
    for parser in _PARSERS:
        if parser.supports(mime_type, filename):
            return parser

    raise ValueError(f"No parser available for file type '{mime_type}' ({filename})")
