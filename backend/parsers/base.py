from abc import ABC, abstractmethod
from typing import Optional

from backend.schemas.models import RawDocument


class DocParser(ABC):
    """文档解析器抽象基类"""

    @abstractmethod
    def parse(self, file_path: str) -> RawDocument:
        """从文件路径解析文档"""
        ...

    @abstractmethod
    def parse_bytes(self, content: bytes, filename: str = "") -> RawDocument:
        """从字节流解析文档"""
        ...

    def _detect_encoding(self, cell_text: str) -> str:
        """规范化单元格文本"""
        return cell_text.strip() if cell_text else ""

    def _clean_text(self, text: str) -> str:
        """清理文本中的空白和零宽字符"""
        import re
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        return text.strip()
