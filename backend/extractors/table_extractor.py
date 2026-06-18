from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


CAPTION_PATTERN = re.compile(
    r"^\s*(?:表|附表|图表|Table)\s*[\d一二三四五六七八九十百\-_.]*\s*[:：、]?\s*(.+)?$",
    re.IGNORECASE,
)
SECTION_PATTERN = re.compile(
    r"^\s*(?:第?[一二三四五六七八九十百]+[章节]|[0-9]+(?:\.[0-9]+){0,4})[、.．\s]+.+"
)
EMPTY_MARKS = {"", "/", "\\", "-", "--", "—", "―", "无", "暂无", "nan", "none", "null"}
NUMERIC_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
RANGE_RE = re.compile(
    r"(?P<a>[-+]?\d+(?:\.\d+)?)\s*(?:~|～|-|－|—|至|到)\s*(?P<b>[-+]?\d+(?:\.\d+)?)"
)
UNIT_HINTS = (
    "mPa·s",
    "mPa.s",
    "m³/min",
    "m3/min",
    "kg/m³",
    "kg/m3",
    "m³",
    "m3",
    "mm",
    "MPa",
    "deg",
    "min",
    "kg",
    "t",
    "m",
    "%",
    "簇",
    "孔",
    "目",
)
HEADER_KEYWORDS = (
    "序号",
    "段号",
    "段序",
    "段数",
    "阶段",
    "工序",
    "工作内容",
    "名称",
    "类型",
    "类别",
    "分类",
    "顶界",
    "底界",
    "顶深",
    "底深",
    "井段",
    "段长",
    "排量",
    "液量",
    "净液量",
    "累计",
    "砂浓度",
    "砂量",
    "支撑剂",
    "液体",
    "粘度",
    "黏度",
    "暂堵",
    "酸",
    "备注",
)


@dataclass
class ParsedNumber:
    raw: str
    numbers: List[float] = field(default_factory=list)
    value: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    unit: str = ""
    is_range: bool = False


@dataclass
class ExtractedTable:
    index: int
    caption: str
    context: List[str]
    row_count: int
    column_count: int
    header_row_indices: List[int]
    headers: List[str]
    records: List[Dict[str, Any]]
    raw_rows: List[List[str]]
    confidence: float
    warnings: List[str] = field(default_factory=list)

    def to_dict(self, include_raw: bool = True) -> Dict[str, Any]:
        data = asdict(self)
        if not include_raw:
            data.pop("raw_rows", None)
        return data


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def compact_cell(value: Any) -> str:
    return clean_text(value).replace("\n", " ").strip()


def normalize_empty(value: str) -> str:
    text = compact_cell(value)
    return "" if text.lower() in EMPTY_MARKS else text


def safe_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def infer_unit_from_text(text: str) -> str:
    low = text.lower()
    for unit in UNIT_HINTS:
        if unit.lower() in low:
            return unit
    unit_match = re.search(r"[（(]\s*([^()（）]{1,20})\s*[)）]", text)
    return unit_match.group(1).strip() if unit_match else ""


def parse_number(text: str) -> ParsedNumber:
    raw = compact_cell(text)
    result = ParsedNumber(raw=raw)
    if not raw:
        return result
    range_match = RANGE_RE.search(raw)
    if range_match:
        a = safe_float(range_match.group("a"))
        b = safe_float(range_match.group("b"))
        if a is not None and b is not None:
            result.numbers = [a, b]
            result.min = min(a, b)
            result.max = max(a, b)
            result.value = result.max
            result.is_range = True
    else:
        nums = [safe_float(m.group(0)) for m in NUMERIC_RE.finditer(raw)]
        result.numbers = [n for n in nums if n is not None]
        if result.numbers:
            result.value = result.numbers[0]
            result.min = min(result.numbers)
            result.max = max(result.numbers)
    result.unit = infer_unit_from_text(raw)
    return result


def make_cell_payload(value: str) -> Dict[str, Any]:
    text = normalize_empty(value)
    parsed = parse_number(text)
    payload: Dict[str, Any] = {"text": text}
    if parsed.numbers:
        payload["number"] = parsed.value
        payload["numbers"] = parsed.numbers
        payload["min"] = parsed.min
        payload["max"] = parsed.max
        payload["is_range"] = parsed.is_range
    if parsed.unit:
        payload["unit"] = parsed.unit
    return payload


def normalize_header_name(text: str, index: int) -> str:
    text = compact_cell(text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("（", "(").replace("）", ")")
    text = text.strip(":：")
    return text or f"column_{index + 1}"


def unique_headers(headers: Sequence[str]) -> List[str]:
    seen: Dict[str, int] = {}
    output: List[str] = []
    for i, header in enumerate(headers):
        name = normalize_header_name(header, i)
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        output.append(name)
    return output


def row_non_empty_count(row: Sequence[str]) -> int:
    return sum(1 for cell in row if normalize_empty(cell))


def row_text(row: Sequence[str]) -> str:
    return " ".join(cell for cell in (compact_cell(c) for c in row) if cell)


def is_likely_caption(text: str) -> bool:
    return bool(text and CAPTION_PATTERN.match(text))


def is_likely_section(text: str) -> bool:
    return bool(text and SECTION_PATTERN.match(text))


def is_mostly_numeric(row: Sequence[str]) -> bool:
    values = [normalize_empty(c) for c in row if normalize_empty(c)]
    if not values:
        return False
    numeric = sum(1 for v in values if parse_number(v).numbers)
    return numeric / max(len(values), 1) >= 0.65


def header_score(row: Sequence[str], next_row: Optional[Sequence[str]] = None) -> float:
    values = [normalize_empty(c) for c in row]
    non_empty = [v for v in values if v]
    if not non_empty:
        return 0.0
    text = row_text(values)
    keyword_hits = sum(1 for kw in HEADER_KEYWORDS if kw in text)
    text_cells = sum(1 for v in non_empty if re.search(r"[\u4e00-\u9fffA-Za-z]", v))
    numeric_cells = sum(1 for v in non_empty if parse_number(v).numbers)
    unit_cells = sum(1 for v in non_empty if infer_unit_from_text(v))
    density = len(non_empty) / max(len(row), 1)
    score = 0.0
    score += min(keyword_hits, 8) * 1.2
    score += text_cells * 0.35
    score += unit_cells * 0.45
    score += density * 1.2
    score -= numeric_cells * 0.25
    if next_row and is_mostly_numeric(next_row):
        score += 1.0
    if is_mostly_numeric(row):
        score -= 2.0
    return score


def infer_header_rows(rows: Sequence[Sequence[str]]) -> Tuple[List[int], float, List[str]]:
    warnings: List[str] = []
    if not rows:
        return [], 0.0, ["empty table"]
    candidate_limit = min(len(rows), 6)
    scores = []
    for i in range(candidate_limit):
        next_row = rows[i + 1] if i + 1 < len(rows) else None
        scores.append((i, header_score(rows[i], next_row)))
    best_index, best_score = max(scores, key=lambda x: x[1])
    if best_score < 1.5:
        warnings.append("header confidence is low; fallback to first non-empty row")
        for i, row in enumerate(rows[:candidate_limit]):
            if row_non_empty_count(row) > 0:
                best_index = i
                break

    header_indices = [best_index]
    if best_index > 0:
        prev_row = rows[best_index - 1]
        prev_score = header_score(prev_row, rows[best_index])
        prev_values = [normalize_empty(c) for c in prev_row if normalize_empty(c)]
        prev_duplicate_groups = len(prev_values) != len(set(prev_values))
        prev_has_header_words = any(kw in row_text(prev_row) for kw in HEADER_KEYWORDS)
        if (
            row_non_empty_count(prev_row) > 0
            and not is_mostly_numeric(prev_row)
            and (prev_score >= 1.2 or prev_duplicate_groups or prev_has_header_words)
        ):
            header_indices.insert(0, best_index - 1)

    if best_index + 1 < len(rows):
        second_score = header_score(rows[best_index + 1], rows[best_index + 2] if best_index + 2 < len(rows) else None)
        second_text = row_text(rows[best_index + 1])
        has_unit_row = bool(re.search(r"[()（）]|单位|m³|m3|MPa|kg|/m|%", second_text))
        if second_score >= best_score * 0.55 and not is_mostly_numeric(rows[best_index + 1]):
            header_indices.append(best_index + 1)
        elif has_unit_row and not is_mostly_numeric(rows[best_index + 1]):
            header_indices.append(best_index + 1)

    confidence = min(max(best_score / 8.0, 0.0), 1.0)
    return header_indices, confidence, warnings


def merge_header_rows(rows: Sequence[Sequence[str]], indices: Sequence[int], column_count: int) -> List[str]:
    merged: List[str] = []
    for col in range(column_count):
        pieces: List[str] = []
        for row_idx in indices:
            row = rows[row_idx]
            cell = normalize_empty(row[col]) if col < len(row) else ""
            if cell and cell not in pieces:
                pieces.append(cell)
        merged.append("".join(pieces))
    return unique_headers(merged)


def pad_row(row: Sequence[str], column_count: int) -> List[str]:
    padded = [compact_cell(c) for c in row[:column_count]]
    if len(padded) < column_count:
        padded.extend([""] * (column_count - len(padded)))
    return padded


def normalize_matrix(matrix: Sequence[Sequence[str]]) -> List[List[str]]:
    if not matrix:
        return []
    column_count = max(len(row) for row in matrix)
    padded = [pad_row(row, column_count) for row in matrix]
    start = 0
    end = len(padded)
    while start < end and row_non_empty_count(padded[start]) == 0:
        start += 1
    while end > start and row_non_empty_count(padded[end - 1]) == 0:
        end -= 1
    return padded[start:end]


def remove_repeated_header_rows(data_rows: Sequence[Sequence[str]], headers: Sequence[str]) -> List[List[str]]:
    normalized_headers = {re.sub(r"\W+", "", h.lower()) for h in headers if h}
    output: List[List[str]] = []
    for row in data_rows:
        text_cells = [re.sub(r"\W+", "", compact_cell(c).lower()) for c in row if compact_cell(c)]
        if text_cells and sum(1 for c in text_cells if c in normalized_headers) >= max(2, len(text_cells) * 0.6):
            continue
        output.append(list(row))
    return output


def rows_to_records(rows: Sequence[Sequence[str]], headers: Sequence[str]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for row_index, row in enumerate(rows, start=1):
        if row_non_empty_count(row) == 0:
            continue
        record: Dict[str, Any] = {"_row_index": row_index}
        for col_index, header in enumerate(headers):
            value = row[col_index] if col_index < len(row) else ""
            record[header] = make_cell_payload(value)
        records.append(record)
    return records


def find_caption(context: Sequence[str]) -> str:
    for text in reversed(context):
        if is_likely_caption(text):
            return text
    for text in reversed(context):
        if text:
            return text[:160]
    return ""


def update_context(context: List[str], paragraph_text: str, max_items: int = 8) -> None:
    text = clean_text(paragraph_text)
    if not text:
        return
    if is_likely_caption(text) or is_likely_section(text) or len(text) <= 180:
        context.append(text)
        del context[:-max_items]


def analyze_table(index: int, raw_rows: List[List[str]], context: List[str]) -> ExtractedTable:
    warnings: List[str] = []
    rows = normalize_matrix(raw_rows)
    if not rows:
        return ExtractedTable(
            index=index,
            caption=find_caption(context),
            context=context[-6:],
            row_count=0,
            column_count=0,
            header_row_indices=[],
            headers=[],
            records=[],
            raw_rows=[],
            confidence=0.0,
            warnings=["empty table"],
        )
    column_count = max(len(row) for row in rows)
    rows = [pad_row(row, column_count) for row in rows]
    header_indices, confidence, header_warnings = infer_header_rows(rows)
    warnings.extend(header_warnings)
    if header_indices:
        headers = merge_header_rows(rows, header_indices, column_count)
        data_start = max(header_indices) + 1
    else:
        headers = unique_headers([f"column_{i + 1}" for i in range(column_count)])
        data_start = 0
    data_rows = remove_repeated_header_rows(rows[data_start:], headers)
    records = rows_to_records(data_rows, headers)
    if len(records) == 0 and len(rows) > 0:
        warnings.append("no data records detected after header inference")
    if column_count >= 12:
        warnings.append("wide table; check merged header columns if downstream mapping looks wrong")
    return ExtractedTable(
        index=index,
        caption=find_caption(context),
        context=context[-6:],
        row_count=len(rows),
        column_count=column_count,
        header_row_indices=header_indices,
        headers=headers,
        records=records,
        raw_rows=rows,
        confidence=round(confidence, 3),
        warnings=warnings,
    )


def table_to_matrix(table: Any) -> List[List[str]]:
    return [[compact_cell(cell.text) for cell in row.cells] for row in table.rows]


def table_text(table: Dict[str, Any]) -> str:
    parts: List[str] = []
    parts.extend(table.get("headers") or [])
    parts.append(table.get("caption") or "")
    for row in table.get("raw_rows") or []:
        parts.extend(row)
    return " ".join(compact_cell(p) for p in parts if compact_cell(p))
