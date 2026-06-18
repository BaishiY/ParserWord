from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.core.analyzer import analyze_document
from backend.core.storage import save_json, save_upload
from backend.parsers.factory import parser_for_file
from backend.schemas.models import ParseResponse


router = APIRouter()


@router.post("/parse-docx", response_model=ParseResponse)
async def parse_docx(file: UploadFile = File(...)) -> ParseResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".doc", ".docx"}:
        raise HTTPException(status_code=400, detail="仅支持 .doc 和 .docx 文件")

    run_id, upload_path = save_upload(file.file, file.filename or f"upload{suffix}")
    try:
        parsed = parser_for_file(upload_path).parse()
        data = analyze_document(parsed, run_id=run_id)
        output_path = save_json(data, run_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc

    return ParseResponse(
        success=True,
        message="解析完成，JSON 已存储",
        run_id=run_id,
        output_path=str(output_path),
        data=data,
    )
