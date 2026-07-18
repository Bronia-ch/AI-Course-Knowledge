"""
FastAPI 应用入口

启动命令：
    uvicorn app.main:app --reload

API 文档：
    http://localhost:8000/docs      Swagger UI
    http://localhost:8000/redoc     ReDoc
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import logging
import os

from . import models  # noqa: F401 — 注册所有模型到 Base.metadata
from .database import init_db
from .config import settings

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加 nvidia cuBLAS DLL 路径（GPU 推理必需）
_cublas_dll_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "venv", "Lib", "site-packages", "nvidia", "cublas", "bin"
)
if os.path.isdir(_cublas_dll_path):
    os.add_dll_directory(_cublas_dll_path)
    os.environ["PATH"] = _cublas_dll_path + ";" + os.environ.get("PATH", "")

# 确保上传目录存在（应用启动时创建）
os.makedirs(os.path.join(settings.UPLOAD_DIR, "audio"), exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：
      1. 初始化数据库表
      2. 加载 Whisper 模型到 GPU/CPU
    关闭时：释放 AI 模型资源
    """
    # ===== 启动事件 =====
    init_db()
    logger.info("数据库表已初始化")

    # 加载 Whisper 模型（单例，存于 app.state）
    from .ai.whisper_transcriber import WhisperTranscriber
    try:
        app.state.whisper_model = WhisperTranscriber(
            model_size=settings.WHISPER_MODEL_SIZE,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
            beam_size=settings.WHISPER_BEAM_SIZE,
        )
        logger.info("Whisper 模型已加载到 app.state.whisper_model")
    except Exception as e:
        logger.warning("Whisper 模型加载失败（GPU 不可用?）: %s", e)
        app.state.whisper_model = None

    yield  # 应用运行期间

    # ===== 关闭事件 =====
    logger.info("应用已关闭")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="AI课程知识库 API",
    description="个人AI课程管理工具 —— 上传音频，AI自动分析生成知识笔记",
    version="0.1.0",
    lifespan=lifespan,
)

# ===== 静态文件 =====
app.mount(
    "/uploads",
    StaticFiles(directory=settings.UPLOAD_DIR),
    name="uploads",
)

# ===== CORS 中间件 =====
# 允许前端开发服务器（Vite 默认端口 5173）跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 根路由 =====
@app.get("/")
def root():
    """健康检查 & 基本信息"""
    return {
        "name": "AI课程知识库 API",
        "version": "0.1.0",
        "status": "running",
    }


# ===== 路由注册 =====
from .routers.courses import router as courses_router
from .routers.chapters import router as chapters_router
from .routers.lessons import router as lessons_router
from .routers.upload import router as upload_router
from .routers.transcription import router as transcription_router
from .routers.analysis import router as analysis_router
from .routers.lesson_data import router as lesson_data_router
from .routers.project_relations import router as project_relations_router
from .routers.progress import router as progress_router

app.include_router(courses_router)
app.include_router(chapters_router)
app.include_router(lessons_router)
app.include_router(upload_router)
app.include_router(transcription_router)
app.include_router(analysis_router)
app.include_router(lesson_data_router)
app.include_router(project_relations_router)
app.include_router(progress_router)
