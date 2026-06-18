from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Tuple
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
JSON_DIR = STORAGE_DIR / "parsed_json"


def ensure_storage_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)


def repair_mojibake(text: Any) -> Any:
    if not isinstance(text, str) or not text:
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    original_cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    repaired_cjk = len(re.findall(r"[\u4e00-\u9fff]", repaired))
    mojibake_marks = sum(text.count(mark) for mark in ("ä", "å", "è", "ç", "æ", "º", ""))
    return repaired if repaired_cjk > original_cjk and mojibake_marks else text


def safe_stem(filename: str) -> str:
    stem = Path(repair_mojibake(filename)).stem or "document"
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", stem)
    stem = re.sub(r"\s+", "_", stem).strip("._")
    return stem[:80] or "document"


def make_run_id(filename: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{ts}_{safe_stem(filename)}_{uuid4().hex[:8]}"


def save_upload(fileobj: BinaryIO, filename: str) -> Tuple[str, Path]:
    ensure_storage_dirs()
    filename = repair_mojibake(filename)
    run_id = make_run_id(filename)
    suffix = Path(filename).suffix.lower()
    upload_path = UPLOAD_DIR / f"{run_id}{suffix}"
    with upload_path.open("wb") as out:
        shutil.copyfileobj(fileobj, out)
    return run_id, upload_path


def save_json(data: Dict[str, Any], run_id: str) -> Path:
    ensure_storage_dirs()
    output_path = JSON_DIR / f"{run_id}.json"
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def validate_run_id(run_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.\-\u4e00-\u9fff]+", run_id or ""):
        raise ValueError("run_id 格式不合法")
    if ".." in run_id:
        raise ValueError("run_id 格式不合法")
    return run_id


def json_path_for_run(run_id: str) -> Path:
    ensure_storage_dirs()
    safe_run_id = validate_run_id(run_id)
    path = (JSON_DIR / f"{safe_run_id}.json").resolve()
    if JSON_DIR.resolve() not in path.parents:
        raise ValueError("run_id 路径不合法")
    return path


def upload_paths_for_run(run_id: str) -> List[Path]:
    ensure_storage_dirs()
    safe_run_id = validate_run_id(run_id)
    return [p for p in UPLOAD_DIR.glob(f"{safe_run_id}.*") if p.is_file()]


def load_json(run_id: str) -> Dict[str, Any]:
    path = json_path_for_run(run_id)
    if not path.exists():
        raise FileNotFoundError("解析结果不存在")
    return json.loads(path.read_text(encoding="utf-8"))


def list_results() -> List[Dict[str, Any]]:
    ensure_storage_dirs()
    results: List[Dict[str, Any]] = []
    for path in sorted(JSON_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        item: Dict[str, Any] = {
            "run_id": path.stem,
            "output_path": str(path),
            "size_bytes": path.stat().st_size,
            "created_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        }
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            item.update(
                {
                    "file_name": repair_mojibake(data.get("file_name")),
                    "well_name": repair_mojibake(data.get("well_name")),
                    "total_stages": data.get("total_stages"),
                    "stage_count": len(data.get("stages") or []),
                    "parsed_at": data.get("parsed_at"),
                }
            )
        except Exception as exc:
            item["warning"] = f"结果摘要读取失败: {type(exc).__name__}"
        results.append(item)
    return results


def delete_result(run_id: str, delete_upload: bool = True) -> Dict[str, Any]:
    json_path = json_path_for_run(run_id)
    deleted_paths: List[str] = []
    if json_path.exists():
        json_path.unlink()
        deleted_paths.append(str(json_path))
    if delete_upload:
        for upload_path in upload_paths_for_run(run_id):
            upload_path.unlink()
            deleted_paths.append(str(upload_path))
    return {"run_id": run_id, "deleted": bool(deleted_paths), "deleted_paths": deleted_paths}
