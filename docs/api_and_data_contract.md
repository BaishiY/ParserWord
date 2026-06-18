# 压裂设计解析后端功能与参数说明

## 1. 总体流程

模块完成一次性闭环：

```text
上传 Word 文件 -> 保存原文件 -> 读取段落和表格 -> 智能分析 -> 生成 JSON -> 存储 JSON -> 返回结果
```

输入文件格式：

- `.docx`
- `.doc`

输出：

- 一个标准 JSON 数据体
- 服务端同时保存一份 `.json` 文件

## 2. API

### 2.1 健康检查

```http
GET /health
```

响应：

```json
{"status": "ok"}
```

### 2.2 上传并解析 Word

```http
POST /api/parse-docx
Content-Type: multipart/form-data
```

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file | File | 是 | 压裂设计 Word 文件，支持 `.doc` / `.docx` |

成功响应：

```json
{
  "success": true,
  "message": "解析完成，JSON 已存储",
  "run_id": "20260617_193000_Y井压裂设计_ab12cd34",
  "output_path": "D:/.../backend/storage/parsed_json/xxx.json",
  "data": {}
}
```

失败响应：

```json
{
  "detail": "ValueError: 仅支持 .doc 和 .docx 文件"
}
```

### 2.3 查询历史解析结果

```http
GET /api/parse-results
```

响应字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| success | boolean | 是否成功 |
| count | number | 结果数量 |
| results | array | 结果摘要列表 |

`results` 每项包含：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| run_id | string | 解析任务 ID |
| output_path | string | JSON 文件路径 |
| size_bytes | number | JSON 文件大小 |
| created_at | string | 文件创建/更新时间 |
| file_name | string/null | 原 Word 文件名 |
| well_name | string/null | 井名 |
| total_stages | number/null | 总段数 |
| stage_count | number/null | 已输出分段数量 |
| parsed_at | string/null | 解析时间 |

### 2.4 查询单个解析结果

```http
GET /api/parse-results/{run_id}
```

响应：

```json
{
  "success": true,
  "run_id": "20260617_193000_Y井压裂设计_ab12cd34",
  "data": {}
}
```

### 2.5 下载 JSON 文件

```http
GET /api/parse-results/{run_id}/download
```

响应为 `application/json` 文件下载。

### 2.6 删除解析结果

```http
DELETE /api/parse-results/{run_id}
```

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| delete_upload | boolean | true | 是否同时删除上传的原始 Word 文件 |

响应：

```json
{
  "success": true,
  "message": "删除完成",
  "run_id": "20260617_193000_Y井压裂设计_ab12cd34",
  "deleted": true,
  "deleted_paths": []
}
```

## 3. 输出 JSON 主结构

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| schema_version | string | 输出结构版本 |
| run_id | string | 本次解析任务 ID |
| source_file | string | 服务端保存后的源文件路径 |
| file_name | string | 源文件名 |
| parsed_at | string | 解析时间 |
| conversion | object | `.doc` 转换信息 |
| well_name | string | 井名 |
| casing_inner_diameter_mm | number/null | 油层套管内径，单位 mm |
| total_stages | number | 压裂总段数 |
| fracturing_fluid_types | array | 压裂液类型 |
| proppant_types | array | 支撑剂类型 |
| temporary_plugging | object | 全局暂堵方案 |
| default_pressure_limit_mpa | number/null | 施工限压，单位 MPa |
| trajectory_data | array | 井斜/轨迹数据 |
| stages | array | 分段数据 |
| raw_extract | object | 原始抽取摘要，用于追溯和调试 |
| warnings | array | 解析警告 |

## 4. 分段数据 stages

每个 `stage` 表示一个压裂段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| stage_number | number | 段序号 |
| top_md_m | number/null | 分段顶界/顶深，单位 m |
| bottom_md_m | number/null | 分段底界/底深，单位 m |
| length_m | number/null | 段长，单位 m |
| cluster_count | number/null | 簇数 |
| classification | string | 中文段分类，如 `主体段`、`风险段`、`渐进防控段` |
| is_first_stage | boolean | 是否首段 |
| design_params | object | 段级设计参数摘要 |
| pump_schedule_template | object | 匹配到的泵注程序模板来源 |
| pump_schedule | array | 泵注程序阶段详情 |
| sources | array | 分段基础数据来源表 |

## 5. design_params 字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| fluid_intensity_m3_per_m | number/null | 用液强度 |
| prop_intensity_t_per_m | number/null | 加砂强度 |
| total_fluid_m3 | number/null | 根据段长和用液强度计算的总液量 |
| total_proppant_t | number/null | 根据段长和加砂强度计算的总砂量 |
| sand_to_ceramic_ratio | string/null | 粉砂与陶粒比例 |
| max_rate_m3_per_min | number | 泵注程序最大排量 |
| min_prop_conc_kg_per_m3 | number | 最低砂浓度 |
| max_prop_conc_kg_per_m3 | number | 最高砂浓度 |
| sand_stage_min_conc_kg_per_m3 | number | 粉砂阶段最低砂浓度 |
| sand_stage_max_conc_kg_per_m3 | number | 粉砂阶段最高砂浓度 |
| ceramic_stage_min_conc_kg_per_m3 | number | 陶粒阶段最低砂浓度 |
| ceramic_stage_max_conc_kg_per_m3 | number | 陶粒阶段最高砂浓度 |
| use_acid | boolean | 是否使用酸液 |
| temporary_plugging_times | number | 暂堵次数 |

## 6. pump_schedule 字段

泵注程序详情按阶段输出：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| sequence | number | 序号 |
| phase | string | 阶段名称 |
| phase_type | string | 阶段类型，如酸液、携砂液、顶替、暂堵 |
| rate_m3_per_min | number | 排量 |
| clean_vol_m3 | number | 阶段净液量 |
| slurry_vol_m3 | number | 携砂液量 |
| prop_conc_kg_per_m3 | number | 砂浓度，整数 |
| fluid_viscosity_mpa_s | number | 液体粘度 |
| cum_vol_m3 | number | 累计液量 |
| cum_slurry_vol_m3 | number | 累计携砂液量 |
| cum_prop_t | number | 累计砂量 |
| fluid_type | string | 液体类型 |
| proppant_type | string | 支撑剂类型 |
| source_row | number | 来源表数据行 |

## 7. 智能化策略

当前采用规则引擎、关键词匹配、正则表达式和上下文分析：

- 不依赖固定表格位置。
- 表头从前 6 行自动评分识别。
- 支持多行表头和 Word 合并表头。
- 段序支持 `段序`、`段号`、`段数`、`序号` 等别名。
- 分类统一转为中文。
- 泵注程序优先选择阶段数最多的长表格。
- 如果某段没有专用泵序，先匹配同分类模板，否则使用最长通用模板。
- 空值、`/`、`-` 等按 0 或空字符串处理。
- 砂浓度输出为整数。

## 8. 当前边界

- 图片内嵌表格暂不做 OCR。
- `.doc` 需要 Windows + Word + pywin32。
- 冲突数据目前保留来源，后续可增加 `conflicts` 字段。
- 对新模板需要继续补充关键词库和规则。
