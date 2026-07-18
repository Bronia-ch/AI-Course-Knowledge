"""
应用配置管理

使用 pydantic-settings 从环境变量或 .env 文件读取配置。
未设置的敏感字段将保持 None，后续接入对应服务时再配置。
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # ===== 数据库 =====
    # SQLite 数据库文件路径（默认存放于 backend 目录下）
    DATABASE_URL: str = "sqlite:///./ai_courses.db"

    # ===== AI 服务 =====
    # DeepSeek API 配置（OpenAI 兼容接口）
    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # ===== 文件上传 =====
    # 上传文件根目录（相对于 backend 目录）
    UPLOAD_DIR: str = "uploads"
    # 单个文件最大大小（字节），默认 500MB
    MAX_UPLOAD_SIZE: int = 524288000
    # 允许的音频文件扩展名
    ALLOWED_AUDIO_EXTENSIONS: str = ".mp3,.wav,.m4a,.ogg,.flac,.aac,.wma"

    # ===== 语音转文字 =====
    # faster-whisper 模型大小，可选: tiny, base, small, medium
    WHISPER_MODEL_SIZE: str = "small"
    # 推理设备: cuda (GPU) 或 cpu
    WHISPER_DEVICE: str = "cuda"
    # 计算精度: float16 / int8 / int8_float16（int8 更省显存）
    WHISPER_COMPUTE_TYPE: str = "int8"
    # beam_size: 越大越准但越慢，建议 1-5
    WHISPER_BEAM_SIZE: int = 5

    model_config = {
        "env_file": ".env",      # 从 .env 文件加载环境变量
        "env_file_encoding": "utf-8",
        "extra": "ignore",       # 忽略未定义的环境变量
    }


# 全局配置实例
settings = Settings()
