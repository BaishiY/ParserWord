"""Layer 2: .doc Word Binary Format 解析器"""
import io
import logging
import struct

import olefile

from backend.parsers.base import DocParser
from backend.schemas.models import RawDocument

logger = logging.getLogger(__name__)

FIB_CCPTEXT_OFFSET = 0x004C
FIB_FCCLX_OFFSET = 0x01A2
FIB_LCBCLX_OFFSET = 0x01A6


class DocParserLegacy(DocParser):
    """
    纯 Python Word Binary Format (.doc) 解析器

    原理：
    1. olefile 打开 OLE2 容器，读取 WordDocument / 1Table 流
    2. 从 FIB 获取 CLX 指针，定位到 Piece Table (Pcdt)
    3. 解析 Pcdt 中的文本映射 (CP → FC)，从 WordDocument 流提取文本

    Pcd 结构中的 fc 字段：
    - bytes 0-1: 标志位
    - bytes 2-3: 16-bit LE 字节偏移（指向 WordDocument 流）
    - fCompressed = byte[1] bit 0
    """

    def parse(self, file_path: str) -> RawDocument:
        with open(file_path, "rb") as f:
            return self.parse_bytes(f.read(), filename=file_path)

    def parse_bytes(self, content: bytes, filename: str = "") -> RawDocument:
        try:
            ole = olefile.OleFileIO(io.BytesIO(content))
        except Exception as e:
            logger.error("无法打开 OLE2: %s", e)
            return RawDocument(paragraphs=[], tables=[], filename=filename)

        try:
            ws = ole.openstream("WordDocument").read()
            ts = None
            for sn in ("1Table", "0Table"):
                if ole.exists(sn):
                    ts = ole.openstream(sn).read()
                    break

            text = self._extract_piece_table_text(ws, ts)
            paras = [self._clean_text(p) for p in text.replace("\r", "\n").split("\n") if self._clean_text(p)]
            return RawDocument(paragraphs=paras, tables=[], filename=filename)
        except Exception as e:
            logger.error("解析 .doc 失败: %s", e)
            return RawDocument(paragraphs=[], tables=[], filename=filename)
        finally:
            ole.close()

    def _extract_piece_table_text(self, ws: bytes, ts: bytes) -> str:
        fcClx = struct.unpack_from("<I", ws, FIB_FCCLX_OFFSET)[0]
        lcbClx = struct.unpack_from("<I", ws, FIB_LCBCLX_OFFSET)[0]

        clx = b""
        if fcClx < len(ws):
            clx = ws[fcClx:fcClx + lcbClx]
        elif ts and fcClx < len(ts):
            clx = ts[fcClx:fcClx + lcbClx]
        if not clx:
            return ""

        pcdt = self._find_pcdt(clx)
        if not pcdt:
            return ""

        total = len(pcdt)
        cp_count = (total + 8) // 12
        aCPs = [struct.unpack_from("<I", pcdt, i * 4)[0] for i in range(cp_count)]
        pcd_base = cp_count * 4

        chunks = []
        for pi in range(cp_count - 1):
            off = pcd_base + pi * 8
            fc = struct.unpack_from("<H", pcdt, off + 2)[0]
            fComp = bool(pcdt[off + 1] & 0x01)

            cp_s, cp_e = aCPs[pi], aCPs[pi + 1]
            n_chars = cp_e - cp_s
            if n_chars <= 0:
                continue

            bpc = 1 if fComp else 2
            sz = n_chars * bpc
            if fc + sz > len(ws):
                sz = len(ws) - fc
            if sz <= 0:
                continue

            raw = ws[fc:fc + sz]
            if bpc == 2:
                raw = raw.decode("utf-16-le", errors="replace").replace("\ufffd", "")
            else:
                raw = raw.decode("cp1252", errors="replace")
            chunks.append(raw)

        return "".join(chunks)

    def _find_pcdt(self, clx: bytes) -> bytes:
        i = 0
        while i < len(clx):
            t = clx[i]
            if t == 0x01:
                cb = struct.unpack_from("<H", clx, i + 1)[0]
                i += 3 + cb
            elif t == 0x02:
                lcb = struct.unpack_from("<I", clx, i + 1)[0]
                return clx[i + 5:i + 5 + lcb]
            else:
                break
        return b""
