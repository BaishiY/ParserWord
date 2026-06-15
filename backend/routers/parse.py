import logging

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.parsers.factory import get_parser
from backend.extractors.table_extractor import extract_from_tables
from backend.extractors.paragraph_extractor import extract_from_paragraphs
from backend.schemas.models import ParseResponse, DataItem

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/api/parse-docx", response_model=ParseResponse)
async def parse_docx(file: UploadFile = File(...)):
    """
    上传 Word 文档（.doc / .docx），解析后返回结构化键值对数据。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")

    # 验证文件扩展名
    ext = file.filename.lower()
    if not (ext.endswith('.doc') or ext.endswith('.docx')):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file.filename}，仅支持 .doc / .docx"
        )

    # 读取文件内容（带大小限制）
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大 (>{MAX_FILE_SIZE // 1024 // 1024}MB)，请压缩后重试"
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="文件为空")

    # 选择解析器
    try:
        head = content[:16]
        parser = get_parser(file.filename, head)
    except Exception as e:
        logger.error("解析器选择失败: %s", e)
        raise HTTPException(status_code=500, detail=f"解析器初始化失败: {e}")

    # 执行解析
    try:
        raw_doc = parser.parse_bytes(content, filename=file.filename)
    except Exception as e:
        logger.error("文档解析失败: %s", e)
        raise HTTPException(status_code=422, detail=f"文档解析失败: {e}")

    # 提取结构化数据
    items: list[DataItem] = []

    # 1) 表格提取（高优先级）
    table_items = extract_from_tables(raw_doc.tables)
    items.extend(table_items)

    # 2) 段落提取（补充）
    para_items = extract_from_paragraphs(raw_doc.paragraphs)
    # 只追加段落中还未出现的键
    table_keys = {item.key for item in table_items}
    for item in para_items:
        if item.key not in table_keys:
            items.append(item)

    # 重新编号
    for i, item in enumerate(items, start=1):
        item.id = i

    if items:
        msg = f"解析完成，共 {len(items)} 条记录"
    else:
        msg = "文档中未识别到结构化数据，请检查文档内容"

    return ParseResponse(items=items, message=msg)
