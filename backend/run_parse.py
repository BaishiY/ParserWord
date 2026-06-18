#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Sequence

from backend.core.analyzer import analyze_document
from backend.core.storage import JSON_DIR, UPLOAD_DIR, ensure_storage_dirs, make_run_id, save_json
from backend.parsers.factory import parser_for_file


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse a frac design Word file and store JSON.")
    parser.add_argument("file", help="Input .doc or .docx file")
    parser.add_argument("-o", "--output", help="Optional output JSON path")
    parser.add_argument("--pretty", action="store_true", help="Print formatted JSON to stdout")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    source = Path(args.file).resolve()
    if not source.exists():
        raise SystemExit(f"文件不存在: {source}")
    if source.suffix.lower() not in {".doc", ".docx"}:
        raise SystemExit("仅支持 .doc 和 .docx 文件")

    ensure_storage_dirs()
    run_id = make_run_id(source.name)
    upload_path = UPLOAD_DIR / f"{run_id}{source.suffix.lower()}"
    shutil.copy2(source, upload_path)

    parsed = parser_for_file(upload_path).parse()
    data = analyze_document(parsed, run_id=run_id)
    output_path = Path(args.output).resolve() if args.output else save_json(data, run_id)
    if args.output:
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.pretty:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
