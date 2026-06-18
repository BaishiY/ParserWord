from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.core.storage import delete_result, json_path_for_run, list_results, load_json
from backend.schemas.models import DeleteResultResponse, ResultDetailResponse, ResultListResponse


router = APIRouter()


@router.get("/parse-results", response_model=ResultListResponse)
def get_parse_results() -> ResultListResponse:
    results = list_results()
    return ResultListResponse(count=len(results), results=results)


@router.get("/parse-results/{run_id}", response_model=ResultDetailResponse)
def get_parse_result(run_id: str) -> ResultDetailResponse:
    try:
        data = load_json(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ResultDetailResponse(run_id=run_id, data=data)


@router.get("/parse-results/{run_id}/download")
def download_parse_result(run_id: str) -> FileResponse:
    try:
        path = json_path_for_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="解析结果不存在")
    return FileResponse(
        path=str(path),
        media_type="application/json",
        filename=f"{run_id}.json",
    )


@router.delete("/parse-results/{run_id}", response_model=DeleteResultResponse)
def remove_parse_result(
    run_id: str,
    delete_upload: bool = Query(True, description="是否同时删除上传的原始 Word 文件"),
) -> DeleteResultResponse:
    try:
        result = delete_result(run_id, delete_upload=delete_upload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result["deleted"]:
        raise HTTPException(status_code=404, detail="解析结果不存在")
    return DeleteResultResponse(message="删除完成", **result)
