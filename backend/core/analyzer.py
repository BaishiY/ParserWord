from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from backend.extractors.paragraph_extractor import extract_key_values
from backend.extractors.table_extractor import NUMERIC_RE, clean_text, parse_number, table_text
from backend.core.storage import repair_mojibake
from backend.parsers.base import ParsedDocument


CATEGORY_ALIASES = {
    "first": "首段",
    "main": "主体段",
    "fracture": "风险段",
    "risk": "风险段",
    "progressive": "渐进防控段",
    "progressive_control": "渐进防控段",
    "difficult": "加砂困难段",
}

FIELD_ALIASES = {
    "stage": ("段序", "段号", "段数", "序号", "阶段序号"),
    "top": ("分段顶界", "顶界", "顶深", "射孔顶界"),
    "bottom": ("分段底界", "底界", "底深", "射孔底界"),
    "length": ("有效段长", "段长", "长度"),
    "category": ("分类", "类别", "类型", "分段类别"),
    "cluster": ("簇数", "簇"),
    "phase": ("阶段名称", "阶段", "工作内容", "工序", "名称"),
    "rate": ("排量", "施工排量"),
    "clean_vol": ("阶段净液量", "净液量", "液量"),
    "slurry_vol": ("携砂液量", "累计携砂液量"),
    "sand_conc": ("砂浓度", "加砂浓度"),
    "viscosity": ("液体粘度", "液体黏度", "粘度", "黏度"),
    "cum_vol": ("累计液量", "累计总液量"),
    "cum_sand": ("累计砂量", "累计加砂量"),
    "stage_sand": ("阶段砂量", "砂量"),
    "fluid_type": ("液体类型", "压裂液类型", "工作液类型"),
    "proppant_type": ("支撑剂类型", "支撑剂", "砂型", "备注"),
}


def first_number(text: str) -> Optional[float]:
    parsed = parse_number(text or "")
    return parsed.value


def all_numbers(text: str) -> List[float]:
    return [float(m.group(0)) for m in NUMERIC_RE.finditer(text or "")]


def cell_text(record: Dict[str, Any], header: str) -> str:
    value = record.get(header)
    if isinstance(value, dict):
        return value.get("text") or ""
    return str(value) if value is not None else ""


def cell_number(record: Dict[str, Any], header: str, default: Optional[float] = None) -> Optional[float]:
    value = record.get(header)
    if isinstance(value, dict):
        number = value.get("number")
        return number if number is not None else default
    return first_number(str(value)) if value is not None else default


def find_header(headers: Sequence[str], aliases: Sequence[str]) -> Optional[str]:
    for alias in aliases:
        for header in headers:
            if alias.lower() in header.lower():
                return header
    return None


def find_exactish_header(headers: Sequence[str], aliases: Sequence[str], excludes: Sequence[str] = ()) -> Optional[str]:
    for alias in aliases:
        for header in headers:
            if any(ex in header for ex in excludes):
                continue
            if alias.lower() in header.lower():
                return header
    return None


def find_headers(headers: Sequence[str], aliases: Sequence[str]) -> List[str]:
    return [h for h in headers if any(a.lower() in h.lower() for a in aliases)]


def table_has(table: Dict[str, Any], keywords: Sequence[str]) -> bool:
    text = table_text(table)
    return all(keyword in text for keyword in keywords)


def table_any(table: Dict[str, Any], keywords: Sequence[str]) -> bool:
    text = table_text(table)
    return any(keyword in text for keyword in keywords)


def normalize_category(text: str, stage_number: Optional[int] = None) -> str:
    raw = clean_text(text)
    if not raw and stage_number == 1:
        return "首段"
    if "首段" in raw or "第一段" in raw or raw == "第1段":
        return "首段"
    if "渐进" in raw:
        return "渐进防控段"
    if "风险" in raw or "裂缝" in raw or "套变" in raw:
        return "风险段"
    if "困难" in raw:
        return "加砂困难段"
    if "主体" in raw:
        return "主体段"
    if raw in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[raw]
    return raw


def category_from_keywords(text: str, stage_number: Optional[int] = None) -> str:
    raw = clean_text(text)
    if stage_number == 1 and not raw:
        return "首段"
    if re.search(r"首段|第\s*1\s*段|第一段", raw):
        return "首段"
    if "渐进" in raw:
        return "渐进防控段"
    if "风险" in raw or "裂缝" in raw or "套变" in raw:
        return "风险段"
    if "困难" in raw:
        return "加砂困难段"
    if "主体" in raw:
        return "主体段"
    if raw in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[raw]
    return ""


def infer_well_name(file_name: str, paragraphs: Sequence[str]) -> str:
    candidates: List[str] = []
    for text in list(paragraphs[:80]):
        for match in re.finditer(r"([\u4e00-\u9fffA-Za-z0-9\-]+井)[\u4e00-\u9fffA-Za-z0-9\-]*(?:压裂|储层|酸化|设计)", text):
            candidates.append(match.group(1))
    stem = Path(repair_mojibake(file_name)).stem
    m = re.search(r"([\u4e00-\u9fffA-Za-z0-9\-]+井)", stem)
    if m:
        candidates.insert(0, m.group(1))
    return repair_mojibake(candidates[0]) if candidates else stem


def extract_casing_inner_diameter(tables: Sequence[Dict[str, Any]], paragraphs: Sequence[str]) -> Optional[float]:
    for table in tables:
        if not table_any(table, ("油层套管", "套管数据", "完井")):
            continue
        header = find_header(table.get("headers") or [], ("内径", "InnerDiameter", "ID"))
        if not header:
            continue
        for record in table.get("records") or []:
            value = cell_number(record, header)
            if value:
                return value
    text = "\n".join(paragraphs)
    for pattern in (r"内径\s*(?:为|=|:|：)?\s*(\d+(?:\.\d+)?)\s*mm", r"内径(\d+(?:\.\d+)?)mm"):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def extract_pressure_limit(paragraphs: Sequence[str], tables: Sequence[Dict[str, Any]]) -> Optional[float]:
    text = "\n".join(paragraphs + [table_text(t) for t in tables])
    patterns = (
        r"(?:泵压|压力|施工压力)[^。\n]{0,12}(?:不超过|控制|限压|小于|低于)\s*(\d+(?:\.\d+)?)\s*MPa",
        r"限压\s*(\d+(?:\.\d+)?)\s*MPa",
        r"控制施工压力\s*(\d+(?:\.\d+)?)\s*MPa以下",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def extract_fluid_types(paragraphs: Sequence[str], tables: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    text = "\n".join(paragraphs + [table_text(t) for t in tables])
    candidates = [
        ("低粘滑溜水", "slickwater_low"),
        ("低黏滑溜水", "slickwater_low"),
        ("滑溜水", "slickwater"),
        ("线性胶", "linear_gel"),
        ("中粘滑溜水", "slickwater_medium"),
        ("中黏滑溜水", "slickwater_medium"),
        ("冻胶", "gel"),
        ("高粘滑溜水", "slickwater_high"),
        ("高黏滑溜水", "slickwater_high"),
        ("酸液", "acid"),
        ("盐酸", "acid"),
    ]
    result: List[Dict[str, Any]] = []
    seen = set()
    for name, key in candidates:
        if name in text and key not in seen:
            item: Dict[str, Any] = {"name": name, "key": key}
            if "酸" in name:
                item["type"] = "盐酸" if "盐酸" in text else "酸液"
            result.append(item)
            seen.add(key)
    return result


def extract_proppants(paragraphs: Sequence[str], tables: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    text = "\n".join(paragraphs + [table_text(t) for t in tables])
    result: List[Dict[str, Any]] = []
    for match in re.finditer(r"(?P<mesh>\d{2,3}/\d{2,3}|\d{2,3})\s*目?\s*(?P<name>石英砂|陶粒|覆膜砂|微支撑剂|粉砂)", text):
        item = {"name": match.group("name"), "mesh": match.group("mesh")}
        if item not in result:
            result.append(item)
    return result


def expand_stage_numbers(text: str) -> List[int]:
    text = clean_text(text)
    result: List[int] = []
    for match in re.finditer(r"(\d+)\s*[~～\-－—至到]\s*(\d+)", text):
        start = int(match.group(1))
        end = int(match.group(2))
        if start <= end and end - start <= 200:
            result.extend(range(start, end + 1))
    remaining = re.sub(r"\d+\s*[~～\-－—至到]\s*\d+", " ", text)
    result.extend(int(n) for n in re.findall(r"\d+", remaining))
    return sorted(set(result))


def is_stage_summary_table(table: Dict[str, Any]) -> bool:
    headers = table.get("headers") or []
    has_stage = find_header(headers, FIELD_ALIASES["stage"])
    has_depth = find_header(headers, FIELD_ALIASES["top"]) or find_header(headers, FIELD_ALIASES["bottom"])
    has_length = find_header(headers, FIELD_ALIASES["length"])
    text = table.get("caption", "") + " " + " ".join(headers)
    return bool(has_stage and (has_depth or has_length) and any(k in text for k in ("分段", "射孔", "段长", "顶界", "底界")))


def row_is_cluster_row(record: Dict[str, Any], headers: Sequence[str]) -> bool:
    text = " ".join(cell_text(record, h) for h in headers)
    has_cluster_detail = any(k in text for k in ("簇间距", "射孔顶界", "射孔底界", "射孔长度"))
    stage_header = find_header(headers, FIELD_ALIASES["stage"])
    stage_text = cell_text(record, stage_header) if stage_header else ""
    return has_cluster_detail and not stage_text


def extract_stage_basics(tables: Sequence[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    stages: Dict[int, Dict[str, Any]] = {}
    for table in tables:
        if not is_stage_summary_table(table):
            continue
        headers = table.get("headers") or []
        stage_h = find_header(headers, FIELD_ALIASES["stage"])
        top_h = find_header(headers, FIELD_ALIASES["top"])
        bottom_h = find_header(headers, FIELD_ALIASES["bottom"])
        length_h = find_header(headers, FIELD_ALIASES["length"])
        category_h = find_header(headers, FIELD_ALIASES["category"])
        cluster_h = find_header(headers, FIELD_ALIASES["cluster"])
        if not stage_h:
            continue
        for record in table.get("records") or []:
            if row_is_cluster_row(record, headers):
                continue
            stage_num = cell_number(record, stage_h)
            if not stage_num or stage_num <= 0:
                continue
            stage_no = int(stage_num)
            stage = stages.setdefault(stage_no, {"stage_number": stage_no, "sources": []})
            if top_h and stage.get("top_md_m") is None:
                stage["top_md_m"] = cell_number(record, top_h)
            if bottom_h and stage.get("bottom_md_m") is None:
                stage["bottom_md_m"] = cell_number(record, bottom_h)
            if length_h and stage.get("length_m") is None:
                stage["length_m"] = cell_number(record, length_h)
            if category_h and not stage.get("classification"):
                stage["classification"] = normalize_category(cell_text(record, category_h), stage_no)
            if cluster_h and stage.get("cluster_count") is None:
                stage["cluster_count"] = cell_number(record, cluster_h)
            stage["sources"].append({"table_index": table.get("index"), "caption": table.get("caption")})
    return stages


def extract_total_stages(stages: Dict[int, Dict[str, Any]], paragraphs: Sequence[str]) -> int:
    if stages:
        return max(stages)
    text = "\n".join(paragraphs)
    matches = re.findall(r"(?:压裂|设计压裂|全井共设计压裂)\s*(\d+)\s*段", text)
    if matches:
        return int(matches[0])
    return 0


def infer_phase_type(text: str) -> str:
    if "酸" in text:
        return "酸液"
    if "暂堵" in text or "投球" in text:
        return "暂堵"
    if "顶替" in text:
        return "顶替"
    if "携砂" in text or "加砂" in text:
        return "携砂液"
    if "前置" in text:
        return "前置液"
    if "桥塞" in text:
        return "送桥塞球"
    return text or "阶段"


def infer_phase_type_for_row(phase: str, row_text: str) -> str:
    phase_type = infer_phase_type(phase)
    if phase_type != phase and phase_type != "阶段":
        return phase_type
    return infer_phase_type(row_text)


def infer_fluid_type(text: str) -> str:
    if "酸" in text:
        return "酸液"
    if "高" in text and ("滑溜水" in text or "压裂液" in text or "线性胶" in text):
        return "高粘滑溜水"
    if "中" in text and "滑溜水" in text:
        return "中粘滑溜水"
    if "线性胶" in text:
        return "线性胶"
    if "滑溜水" in text:
        return "滑溜水"
    if "冻胶" in text:
        return "冻胶"
    return ""


def infer_proppant_type(text: str) -> str:
    match = re.search(r"(\d{2,3}/\d{2,3}|\d{2,3})\s*目?\s*(石英砂|陶粒|覆膜砂|微支撑剂|粉砂)", text)
    if match:
        return f"{match.group(1)}目{match.group(2)}"
    for name in ("陶粒", "石英砂", "粉砂", "覆膜砂", "微支撑剂"):
        if name in text:
            return name
    return ""


def is_pump_schedule_table(table: Dict[str, Any]) -> bool:
    headers = table.get("headers") or []
    text = table_text(table)
    has_phase = find_header(headers, FIELD_ALIASES["phase"])
    has_numeric = any(find_header(headers, FIELD_ALIASES[key]) for key in ("rate", "clean_vol", "sand_conc", "cum_vol"))
    keyword = any(k in text for k in ("泵注", "泵序", "压裂泵注程序", "施工泵序", "阶段", "砂浓度"))
    return bool(has_phase and has_numeric and keyword)


def normalize_number(value: Optional[float], integer: bool = False) -> float:
    if value is None:
        return 0
    return int(round(value)) if integer else value


def extract_pump_schedule_from_table(table: Dict[str, Any]) -> List[Dict[str, Any]]:
    headers = table.get("headers") or []
    phase_h = find_header(headers, FIELD_ALIASES["phase"])
    rate_h = find_header(headers, FIELD_ALIASES["rate"])
    clean_h = find_header(headers, FIELD_ALIASES["clean_vol"])
    slurry_h = find_header(headers, FIELD_ALIASES["slurry_vol"])
    conc_h = find_header(headers, FIELD_ALIASES["sand_conc"])
    viscosity_h = find_header(headers, FIELD_ALIASES["viscosity"])
    cum_vol_h = find_header(headers, FIELD_ALIASES["cum_vol"])
    cum_sand_h = find_header(headers, FIELD_ALIASES["cum_sand"])
    fluid_h = find_exactish_header(headers, FIELD_ALIASES["fluid_type"], excludes=("粘度", "黏度", "液量"))
    proppant_h = find_header(headers, FIELD_ALIASES["proppant_type"])

    schedule: List[Dict[str, Any]] = []
    for idx, record in enumerate(table.get("records") or [], start=1):
        row_text = " ".join(cell_text(record, h) for h in headers)
        if not row_text.strip():
            continue
        phase = cell_text(record, phase_h) if phase_h else ""
        if phase.strip().isdigit():
            phase = f"阶段{phase.strip()}"
        if not phase:
            phase = infer_phase_type(row_text)
        fluid_type = cell_text(record, fluid_h) if fluid_h else ""
        proppant_type = cell_text(record, proppant_h) if proppant_h else ""
        fluid_type = fluid_type or infer_fluid_type(phase + " " + row_text)
        proppant_type = infer_proppant_type(proppant_type or row_text)
        item = {
            "sequence": idx,
            "phase": phase,
            "phase_type": infer_phase_type_for_row(phase, row_text),
            "rate_m3_per_min": normalize_number(cell_number(record, rate_h) if rate_h else None),
            "clean_vol_m3": normalize_number(cell_number(record, clean_h) if clean_h else None),
            "slurry_vol_m3": normalize_number(cell_number(record, slurry_h) if slurry_h else None),
            "prop_conc_kg_per_m3": normalize_number(cell_number(record, conc_h) if conc_h else None, integer=True),
            "fluid_viscosity_mpa_s": normalize_number(cell_number(record, viscosity_h) if viscosity_h else None),
            "cum_vol_m3": normalize_number(cell_number(record, cum_vol_h) if cum_vol_h else None),
            "cum_slurry_vol_m3": normalize_number(cell_number(record, slurry_h) if slurry_h else None),
            "cum_prop_t": normalize_number(cell_number(record, cum_sand_h) if cum_sand_h else None),
            "fluid_type": fluid_type,
            "proppant_type": proppant_type,
            "source_row": record.get("_row_index"),
        }
        schedule.append(item)
    return schedule


def classify_pump_template(table: Dict[str, Any]) -> str:
    heading = current_pump_heading(table)
    text = heading or table.get("caption", "")
    explicit = re.findall(r"[（(]\s*\d+\s*[）)]\s*([^：:。\n]{1,24})泵序", text)
    if explicit:
        category = category_from_keywords(explicit[-1])
        if category:
            return category
    if re.search(r"第\s*1\s*段泵序|第1段泵序|首段泵序", text):
        return "首段"
    category = category_from_keywords(text)
    return category or "通用"


def current_pump_heading(table: Dict[str, Any]) -> str:
    for line in reversed(table.get("context") or []):
        text = clean_text(line)
        if "下表" in text or "表格" in text:
            continue
        if re.search(r"(第\s*[\d、,~～\-－—至到]+\s*段|主体段|风险段|渐进防控段|首段|第一段).{0,30}泵序\s*[:：]?$", text):
            return text
        if re.search(r"泵注程序\s*$", text):
            return line
    return ""


def extract_template_stage_numbers(template: Dict[str, Any]) -> List[int]:
    text = template.get("pump_heading") or template.get("caption") or ""
    scoped: List[int] = []
    for match in re.finditer(r"第\s*([\d、,~～\-－—至到]+)\s*段", text):
        scoped.extend(expand_stage_numbers(match.group(1)))
    for match in re.finditer(r"第\s*([\d、,~～\-－—至到]+)(?=[）)])", text):
        scoped.extend(expand_stage_numbers(match.group(1)))
    return sorted(set(scoped))


def extract_pump_templates(tables: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    templates: List[Dict[str, Any]] = []
    for table in tables:
        if not is_pump_schedule_table(table):
            continue
        schedule = extract_pump_schedule_from_table(table)
        if not schedule:
            continue
        templates.append(
            {
                "table_index": table.get("index"),
                "caption": table.get("caption"),
                "context_text": " ".join(table.get("context") or []),
                "pump_heading": current_pump_heading(table),
                "classification": classify_pump_template(table),
                "stage_count": len(schedule),
                "schedule": schedule,
            }
        )
    templates.sort(key=lambda item: item["stage_count"], reverse=True)
    return templates


def choose_template_for_stage(stage: Dict[str, Any], templates: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not templates:
        return None
    stage_number = stage.get("stage_number")
    for template in templates:
        if stage_number in extract_template_stage_numbers(template):
            return template
    classification = stage.get("classification") or ""
    for template in templates:
        if classification and template.get("classification") == classification:
            return template
    if stage.get("stage_number") == 1:
        for template in templates:
            if template.get("classification") == "首段":
                return template
    return templates[0]


def summarize_schedule(schedule: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    rates = [item.get("rate_m3_per_min") for item in schedule if item.get("rate_m3_per_min")]
    concs = [item.get("prop_conc_kg_per_m3") for item in schedule if item.get("prop_conc_kg_per_m3")]
    sand_concs = [
        item.get("prop_conc_kg_per_m3")
        for item in schedule
        if item.get("prop_conc_kg_per_m3") and any(k in (item.get("proppant_type") or item.get("phase") or "") for k in ("粉砂", "石英砂", "70/140", "100"))
    ]
    ceramic_concs = [
        item.get("prop_conc_kg_per_m3")
        for item in schedule
        if item.get("prop_conc_kg_per_m3") and any(k in (item.get("proppant_type") or item.get("phase") or "") for k in ("陶粒", "40/70"))
    ]
    temp_plugging_times = sum(1 for item in schedule if re.search(r"暂堵|投球", item.get("phase") or ""))
    return {
        "max_rate_m3_per_min": max(rates) if rates else 0,
        "min_prop_conc_kg_per_m3": min(concs) if concs else 0,
        "max_prop_conc_kg_per_m3": max(concs) if concs else 0,
        "sand_stage_min_conc_kg_per_m3": min(sand_concs) if sand_concs else 0,
        "sand_stage_max_conc_kg_per_m3": max(sand_concs) if sand_concs else 0,
        "ceramic_stage_min_conc_kg_per_m3": min(ceramic_concs) if ceramic_concs else 0,
        "ceramic_stage_max_conc_kg_per_m3": max(ceramic_concs) if ceramic_concs else 0,
        "use_acid": any("酸" in (item.get("phase") or "") or item.get("fluid_type") == "酸液" for item in schedule),
        "temporary_plugging_times": temp_plugging_times,
    }


def extract_global_temporary_plugging(paragraphs: Sequence[str], tables: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    text = "\n".join(paragraphs + [table_text(t) for t in tables if table_any(t, ("暂堵",))])
    balls = []
    for count, size in re.findall(r"(\d+)\s*颗\s*(\d+(?:\.\d+)?)\s*mm\s*暂堵球", text):
        balls.append({"count": int(count), "size_mm": float(size)})
    agents = []
    for weight in re.findall(r"(\d+(?:\.\d+)?)\s*kg\s*暂堵剂", text):
        agents.append({"weight_kg": float(weight)})
    no_temp = bool(re.search(r"本井不暂堵|全井不暂堵|均不暂堵|不进行暂堵", text))
    times = 0
    if "两次" in text or "2次" in text:
        times = 2
    elif "一次" in text or "1次" in text or balls or agents:
        times = 1
    return {
        "used": bool((balls or agents or times) and not no_temp),
        "times": 0 if no_temp else times,
        "balls": balls,
        "agents": agents,
        "source_summary": text[:600],
    }


def extract_trajectory(tables: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for table in tables:
        text = table_text(table)
        if not any(k in text for k in ("井斜数据", "井眼轨迹", "测深")):
            continue
        headers = table.get("headers") or []
        md_h = find_header(headers, ("测深", "井深", "MD"))
        inc_h = find_header(headers, ("井斜", "inclination"))
        tvd_h = find_header(headers, ("垂深", "TVD"))
        if not md_h or not inc_h:
            continue
        for record in table.get("records") or []:
            md = cell_number(record, md_h)
            inc = cell_number(record, inc_h)
            if md is None or inc is None:
                continue
            point = {"md_m": md, "inclination_deg": inc}
            if tvd_h:
                point["tvd_m"] = cell_number(record, tvd_h, 0)
            result.append(point)
    return result


def derive_stage_params_from_text(stage: Dict[str, Any], paragraphs: Sequence[str]) -> Dict[str, Any]:
    text = "\n".join(paragraphs)
    category = stage.get("classification") or ""
    params: Dict[str, Any] = {}
    category_keys = [category]
    if category == "渐进防控段":
        category_keys.append("渐进段")
    for key in category_keys:
        if not key:
            continue
        pattern = key + r"[^。\n]{0,80}?用液强度\s*(\d+(?:\.\d+)?)(?:\s*[~～\-－—至到]\s*(\d+(?:\.\d+)?))?"
        match = re.search(pattern, text)
        if match:
            nums = [float(n) for n in match.groups() if n]
            params["fluid_intensity_m3_per_m"] = max(nums) if nums else None
        pattern = key + r"[^。\n]{0,80}?加砂强度\s*(\d+(?:\.\d+)?)(?:\s*[~～\-－—至到]\s*(\d+(?:\.\d+)?))?"
        match = re.search(pattern, text)
        if match:
            nums = [float(n) for n in match.groups() if n]
            params["prop_intensity_t_per_m"] = max(nums) if nums else None
    ratio = re.search(r"(\d+)\s*[:：]\s*(\d+)", text)
    if ratio:
        params["sand_to_ceramic_ratio"] = f"{ratio.group(1)}:{ratio.group(2)}"
    return params


def build_stages(
    stages: Dict[int, Dict[str, Any]], templates: Sequence[Dict[str, Any]], paragraphs: Sequence[str]
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for stage_no in sorted(stages):
        stage = stages[stage_no]
        if not stage.get("classification"):
            stage["classification"] = "首段" if stage_no == 1 else ""
        template = choose_template_for_stage(stage, templates)
        schedule = template["schedule"] if template else []
        summary = summarize_schedule(schedule)
        design_params = derive_stage_params_from_text(stage, paragraphs)
        design_params.update(summary)
        if stage.get("length_m") and design_params.get("fluid_intensity_m3_per_m"):
            design_params["total_fluid_m3"] = round(stage["length_m"] * design_params["fluid_intensity_m3_per_m"], 3)
        if stage.get("length_m") and design_params.get("prop_intensity_t_per_m"):
            design_params["total_proppant_t"] = round(stage["length_m"] * design_params["prop_intensity_t_per_m"], 3)
        result.append(
            {
                "stage_number": stage_no,
                "top_md_m": stage.get("top_md_m"),
                "bottom_md_m": stage.get("bottom_md_m"),
                "length_m": stage.get("length_m"),
                "cluster_count": stage.get("cluster_count"),
                "classification": normalize_category(stage.get("classification") or "", stage_no),
                "is_first_stage": stage_no == 1,
                "design_params": design_params,
                "pump_schedule_template": {
                    "table_index": template.get("table_index") if template else None,
                    "caption": template.get("caption") if template else "",
                    "classification": template.get("classification") if template else "",
                },
                "pump_schedule": schedule,
                "sources": stage.get("sources", []),
            }
        )
    return result


def analyze_document(parsed: ParsedDocument, run_id: str) -> Dict[str, Any]:
    paragraphs = parsed.paragraphs
    tables = parsed.tables
    stage_basics = extract_stage_basics(tables)
    pump_templates = extract_pump_templates(tables)
    stages = build_stages(stage_basics, pump_templates, paragraphs)

    data = {
        "schema_version": "0.1.0",
        "run_id": run_id,
        "source_file": repair_mojibake(str(parsed.original_path)),
        "file_name": repair_mojibake(parsed.original_path.name),
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
        "conversion": parsed.conversion,
        "well_name": infer_well_name(parsed.original_path.name, paragraphs),
        "casing_inner_diameter_mm": extract_casing_inner_diameter(tables, paragraphs),
        "total_stages": extract_total_stages(stage_basics, paragraphs),
        "fracturing_fluid_types": extract_fluid_types(paragraphs, tables),
        "proppant_types": extract_proppants(paragraphs, tables),
        "temporary_plugging": extract_global_temporary_plugging(paragraphs, tables),
        "default_pressure_limit_mpa": extract_pressure_limit(paragraphs, tables),
        "trajectory_data": extract_trajectory(tables),
        "stages": stages,
        "raw_extract": {
            "paragraph_count": len(paragraphs),
            "table_count": len(tables),
            "key_values": extract_key_values(paragraphs),
            "tables": [
                {
                    "index": table.get("index"),
                    "caption": table.get("caption"),
                    "headers": table.get("headers"),
                    "row_count": table.get("row_count"),
                    "column_count": table.get("column_count"),
                    "confidence": table.get("confidence"),
                    "warnings": table.get("warnings"),
                }
                for table in tables
            ],
        },
        "warnings": parsed.warnings,
    }
    return data
