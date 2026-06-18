from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.parse import router as parse_router
from backend.routers.results import router as results_router


app = FastAPI(
    title="Frac Design Parser API",
    description="读取、分析并存储压裂设计 Word 文档的 Python 后端服务。",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parse_router, prefix="/api", tags=["parse"])
app.include_router(results_router, prefix="/api", tags=["results"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
