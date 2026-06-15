"""Layer 1: .docx 核心解析器"""
import io
from typing import Optional

from docx import Document as DocxDocument
from docx.table import Table as DocxTable

from backend.parsers.base import DocParser
from backend.schemas.models import RawDocument


class DocxParser(DocParser):
    """
    .docx 解析器 — 主干道，覆盖 90%+ 现代文档

    原理：python-docx 直接解压二进制流，读取 word/document.xml，
    在 XML 树中表格由 <w:tbl> 包裹，行 <w:tr>，列 <w:tc>，
    以结构化方式还原全部内容，不会粘连。
    """

    def parse(self, file_path: str) -> RawDocument:
        doc = DocxDocument(file_path)
        return self._extract(doc, filename=file_path)

    def parse_bytes(self, content: bytes, filename: str = "") -> RawDocument:
        doc = DocxDocument(io.BytesIO(content))
        return self._extract(doc, filename=filename)

    def _extract(self, doc: DocxDocument, filename: str = "") -> RawDocument:
        paragraphs = []
        for p in doc.paragraphs:
            text = self._clean_text(p.text)
            if text:
                paragraphs.append(text)

        tables = []
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [self._clean_text(cell.text) for cell in row.cells]
                # 跳过全空行
                if any(cell for cell in row_data):
                    table_data.append(row_data)
            if table_data:
                tables.append(table_data)

        return RawDocument(
            paragraphs=paragraphs,
            tables=tables,
            filename=filename
        )
