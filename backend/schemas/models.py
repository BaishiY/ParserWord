from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ParseResponse(BaseModel):
    success: bool = Field(..., description="是否解析成功")
    message: str = Field(..., description="处理结果说明")
    run_id: str = Field(..., description="本次解析任务 ID")
    output_path: str = Field(..., description="服务端 JSON 存储路径")
    data: Dict[str, Any] = Field(..., description="解析后的 JSON 数据体")


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: Optional[str] = None


class ResultSummary(BaseModel):
    run_id: str
    output_path: str
    size_bytes: int
    created_at: str
    file_name: Optional[str] = None
    well_name: Optional[str] = None
    total_stages: Optional[int] = None
    stage_count: Optional[int] = None
    parsed_at: Optional[str] = None
    warning: Optional[str] = None


class ResultListResponse(BaseModel):
    success: bool = True
    count: int
    results: List[ResultSummary]


class ResultDetailResponse(BaseModel):
    success: bool = True
    run_id: str
    data: Dict[str, Any]


class DeleteResultResponse(BaseModel):
    success: bool = True
    message: str
    run_id: str
    deleted: bool
    deleted_paths: List[str]
