from __future__ import annotations

from pathlib import Path

from backend.parsers.base import DocParser
from backend.parsers.doc_parser import LegacyDocParser
from backend.parsers.docx_parser import DocxParser


def parser_for_file(file_path: Path) -> DocParser:
    suffix = file_path.suffix.lower()
    if suffix == ".docx":
        return DocxParser(file_path)
    if suffix == ".doc":
        return LegacyDocParser(file_path)
    raise ValueError("仅支持 .doc 和 .docx 文件")
