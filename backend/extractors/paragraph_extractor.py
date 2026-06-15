import logging
import re
from backend.schemas.models import DataItem

logger = logging.getLogger(__name__)

KV_PATTERN = re.compile(r'^(.+?)[：:]\s*(.+)$')

SKIP_PATTERNS = [
    re.compile(r'^第[一二三四五六七八九十\d]+[章节篇部]'),
]

def extract_from_paragraphs(paragraphs: list[str]) -> list[DataItem]:
    items: list[DataItem] = []
    seen_keys: set[str] = set()
    _id = [0]

    def add_item(key: str, value: str):
        k = key.strip().rstrip('\uff1a:\t ')
        v = value.strip()
        if k and v:
            dedup_key = k
            suffix = 1
            while dedup_key in seen_keys:
                suffix += 1
                dedup_key = f'{k}_{suffix}'
            seen_keys.add(dedup_key)
            _id[0] += 1
            items.append(DataItem(id=_id[0], key=dedup_key, value=v))

    for para in paragraphs:
        if any(p.match(para) for p in SKIP_PATTERNS):
            continue
        match = KV_PATTERN.match(para)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            if len(key) <= 40:
                add_item(key, value)

    return items
