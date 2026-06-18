from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.extractors.table_extractor import clean_text, parse_number


KEY_VALUE_RE = re.compile(
    r"(?P<key>[\u4e00-\u9fffA-Za-z0-9_（）()/%·.\-]{2,30})\s*[:：]\s*(?P<value>[^；;，,\n]{1,80})"
)


def extract_key_values(paragraphs: List[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for idx, paragraph in enumerate(paragraphs):
        text = clean_text(paragraph)
        if not text:
            continue
        for match in KEY_VALUE_RE.finditer(text):
            key = match.group("key").strip()
            value = match.group("value").strip()
            parsed = parse_number(value)
            item: Dict[str, Any] = {
                "paragraph_index": idx,
                "key": key,
                "value": value,
                "source_text": text,
            }
            if parsed.numbers:
                item["number"] = parsed.value
                item["numbers"] = parsed.numbers
                item["min"] = parsed.min
                item["max"] = parsed.max
                item["unit"] = parsed.unit
            items.append(item)
    return items


def surrounding_text(paragraphs: List[str], keyword: str, window: int = 2) -> List[str]:
    hits: List[str] = []
    for idx, paragraph in enumerate(paragraphs):
        if keyword in paragraph:
            start = max(0, idx - window)
            end = min(len(paragraphs), idx + window + 1)
            hits.append("\n".join(paragraphs[start:end]))
    return hits
