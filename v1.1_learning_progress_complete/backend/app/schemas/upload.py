"""
上传相关 Schema — 音频文件信息
"""

from pydantic import BaseModel


class AudioInfoResponse(BaseModel):
    """音频文件信息响应"""
    lesson_id: int
    file_name: str           # 原始文件名
    file_path: str           # 存储的相对路径
    file_size: int           # 文件大小（字节）
    file_extension: str      # 文件扩展名
    exists: bool             # 文件是否存在
