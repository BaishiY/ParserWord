"""表格提取器 — 从 RawDocument.tables 中提取结构化 key-value 数据"""
import logging
import re

from backend.schemas.models import DataItem

logger = logging.getLogger(__name__)


def extract_from_tables(tables: list[list[list[str]]]) -> list[DataItem]:
    """
    从所有表格中提取 key-value 数据项。

    提取策略（按优先级）：
    1. 双列表格 → 第一列 = key, 第二列 = value
    2. 多列表格 → 首行作为 key，后续行作为 value 列表
    3. 标题行合并值 → 考虑 colspan/rowspan 平铺
    """
    items: list[DataItem] = []
    seen_keys: set[str] = set()
    _id = [0]  # 用 list 包裹以在嵌套闭包中修改

    def add_item(key: str, value: str):
        k = key.strip().rstrip(':：\t ')
        v = value.strip()
        if k and v:
            # 去重：相同 key 追加序号
            dedup_key = k
            suffix = 1
            while dedup_key in seen_keys:
                suffix += 1
                dedup_key = f"{k}_{suffix}"
            seen_keys.add(dedup_key)
            _id[0] += 1
            items.append(DataItem(id=_id[0], key=dedup_key, value=v))

    for table in tables:
        if not table:
            continue

        row_count = len(table)
        col_count = max(len(row) for row in table) if table else 0

        # --- 策略 1：标准双列表格 ---
        if col_count == 2:
            for row in table:
                if len(row) >= 2:
                    add_item(row[0], row[1])
            continue

        # --- 策略 2：多列表格，首行为表头 ---
        if row_count >= 2 and col_count >= 3:
            headers = table[0]
            for row_idx in range(1, row_count):
                row = table[row_idx]
                for col_idx, header in enumerate(headers):
                    if col_idx < len(row) and header.strip():
                        add_item(header, row[col_idx])
            continue

        # --- 策略 3：一列表格或无结构表，扁平化处理 ---
        for row in table:
            row_text = ' | '.join(cell.strip() for cell in row if cell.strip())
            if row_text:
                # 尝试从行文本中提取 key: value 模式
                match = re.match(r'^(.+?)[：:]\s*(.+)$', row_text)
                if match:
                    add_item(match.group(1), match.group(2))
                else:
                    add_item(f"参数_{_id[0] + 1}", row_text)

    return items
