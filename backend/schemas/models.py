from pydantic import BaseModel
from typing import Optional


class DataItem(BaseModel):
    """单个键值对数据项"""
    id: int
    key: str
    value: str


class ParseResponse(BaseModel):
    """文档解析结果响应"""
    items: list[DataItem]
    message: Optional[str] = None


class RawDocument(BaseModel):
    """文档原始解析结果（内部模型，不对外暴露）"""
    paragraphs: list[str]
    tables: list[list[list[str]]]  # tables[row][col] = cell_text
    filename: str = ""
