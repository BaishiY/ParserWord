"""解析器工厂 — 根据文件头/后缀选择解析器"""
import logging

from backend.parsers.base import DocParser
from backend.parsers.docx_parser import DocxParser
from backend.parsers.doc_parser import DocParserLegacy

logger = logging.getLogger(__name__)


def get_parser(filename: str, content_head: bytes) -> DocParser:
    """
    根据文件类型检测选择解析器

    检测顺序：
    1. 前 4 字节 magic → PK.. = ZIP/.docx, D0CF = OLE2/.doc
    2. 后缀名兜底
    """
    docx_parser = DocxParser()
    doc_parser = DocParserLegacy()

    # Magic bytes 检测（优先级高）
    if len(content_head) >= 4:
        # PK\x03\x04 — ZIP 格式（.docx 本质是 ZIP 容器）
        if content_head[:2] == b'PK':
            logger.debug("Magic PK -> .docx，使用 DocxParser")
            return docx_parser

        # \xD0\xCF\x11\xE0 — OLE2/CFB 格式（.doc）
        if content_head[:4] == b'\xD0\xCF\x11\xE0':
            logger.debug("Magic OLE2 -> .doc，使用 DocParserLegacy")
            return doc_parser

    # 后缀名兜底
    lower_name = filename.lower()
    if lower_name.endswith('.docx'):
        return docx_parser
    elif lower_name.endswith('.doc'):
        return doc_parser

    # 默认走 .docx 解析器（更安全）
    logger.warning("无法识别文件类型 %s (magic=%s)，默认使用 DocxParser", filename, content_head[:8].hex())
    return docx_parser
