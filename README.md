# 压裂设计智能解析模块

本项目是压裂设计 Word 文档解析后端，目标流程为：

1. 读取 `.doc` / `.docx` 文件
2. 分析段落、表格和关键参数
3. 生成标准 JSON 数据体
4. 将 JSON 存储到本地目录，供 Web 端或下游模块调用

## 项目结构

```text
backend/
|-- main.py                    # FastAPI 入口，默认端口 8000
|-- requirements.txt           # 后端依赖
|-- routers/
|   `-- parse.py               # POST /api/parse-docx
|-- parsers/
|   |-- base.py                # 解析器抽象类
|   |-- docx_parser.py         # .docx 读取
|   |-- doc_parser.py          # .doc 转 .docx 后读取
|   `-- factory.py             # 根据文件类型选择解析器
|-- extractors/
|   |-- table_extractor.py     # 表格结构化、表头识别、数值解析
|   `-- paragraph_extractor.py # 段落 key:value 提取
|-- schemas/
|   `-- models.py              # API 响应模型
|-- core/
|   |-- analyzer.py            # 压裂设计业务分析
|   `-- storage.py             # 上传文件与 JSON 存储
`-- run_parse.py               # 命令行解析入口
```

## 安装依赖

```powershell
cd D:\agent_project\泵控程序开发\压裂设计解析模块
python -m pip install -r backend\requirements.txt
```

`.doc` 文件解析依赖 Windows、Microsoft Word 和 `pywin32`；如果环境不满足，可以先把 `.doc` 另存为 `.docx`。

## 启动后端

```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

健康检查：

```text
GET /health
```

解析接口：

```text
POST /api/parse-docx
Content-Type: multipart/form-data
file: .doc 或 .docx
```

结果接口：

```text
GET    /api/parse-results
GET    /api/parse-results/{run_id}
GET    /api/parse-results/{run_id}/download
DELETE /api/parse-results/{run_id}
```

## 命令行解析

```powershell
python -m backend.run_parse "Y井压裂设计.docx"
```

指定输出文件：

```powershell
python -m backend.run_parse "Y井压裂设计.docx" -o "output.json"
```

## 存储位置

- 上传原文件：`backend/storage/uploads/`
- 解析 JSON：`backend/storage/parsed_json/`

这些目录会在运行时自动创建。

## 启动前端

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

开发环境前端地址：

```text
http://127.0.0.1:5173
```

前端已经在 `frontend/vite.config.ts` 中配置代理：

```text
/api    -> http://localhost:8000
/health -> http://localhost:8000
```

所以前端代码里可以直接请求 `/api/parse-docx`、`/api/parse-results` 等路径。

## 当前能力

- 支持 `.docx` 表格和段落读取
- 支持 `.doc` 自动转换后读取
- 智能识别表名、上下文、多行表头、合并表头
- 表格单元格解析文本、数字、范围和单位
- 提取井名、套管内径、施工限压、压裂液、支撑剂、暂堵方案
- 识别分段表，生成每段基础参数
- 识别泵注程序表，生成阶段列表
- 统计最大排量、砂浓度范围、暂堵次数、是否用酸
- 输出中文压裂段分类

详细字段说明见 [docs/api_and_data_contract.md](docs/api_and_data_contract.md)。
