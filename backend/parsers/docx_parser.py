from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from backend.extractors.table_extractor import analyze_table, clean_text, table_to_matrix, update_context
from backend.parsers.base import DocParser, ParsedDocument


def iter_block_items(doc: Any) -> Iterable[Any]:
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, doc)
        elif child.tag.endswith("}tbl"):
            yield Table(child, doc)


class DocxParser(DocParser):
    def parse(self) -> ParsedDocument:
        doc = Document(str(self.file_path))
        paragraphs: List[str] = []
        tables = []
        context: List[str] = []
        table_index = 0

        for block in iter_block_items(doc):
            if isinstance(block, Paragraph):
                text = clean_text(block.text)
                if text:
                    paragraphs.append(text)
                update_context(context, text)
                continue

            if isinstance(block, Table):
                table_index += 1
                matrix = table_to_matrix(block)
                extracted = analyze_table(table_index, matrix, list(context))
                tables.append(extracted.to_dict(include_raw=True))

        return ParsedDocument(
            source_path=self.file_path,
            original_path=self.file_path,
            paragraphs=paragraphs,
            tables=tables,
            conversion={"converted": False},
        )
