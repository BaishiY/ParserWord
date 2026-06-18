from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

try:
    import win32com.client

    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False

from backend.parsers.base import DocParser, ParsedDocument
from backend.parsers.docx_parser import DocxParser


class LegacyDocParser(DocParser):
    def parse(self) -> ParsedDocument:
        if not WIN32COM_AVAILABLE:
            raise RuntimeError(
                ".doc 文件解析需要 Windows 环境、Microsoft Word 和 pywin32。"
                "也可以先手动另存为 .docx。"
            )

        temp_dir = Path(tempfile.mkdtemp(prefix="frac_doc_convert_"))
        out_path = temp_dir / f"{self.file_path.stem}.docx"
        word = None
        doc = None
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            doc = word.Documents.Open(str(self.file_path.resolve()))
            doc.SaveAs2(str(out_path), FileFormat=16)
            parsed = DocxParser(out_path).parse()
            parsed.original_path = self.file_path
            parsed.conversion = {
                "converted": True,
                "method": "win32com",
                "temporary_docx": str(out_path),
            }
            return parsed
        finally:
            if doc is not None:
                doc.Close(False)
            if word is not None:
                word.Quit()
            shutil.rmtree(temp_dir, ignore_errors=True)
