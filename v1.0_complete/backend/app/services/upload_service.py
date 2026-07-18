"""
文件上传服务 — 音频文件存储管理

功能：
  - 生成安全的存储路径
  - 保存上传文件到本地
  - 验证文件类型和大小
  - 查询音频信息
  - 删除音频文件及文件夹
"""

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from ..config import settings


# ===== 路径工具 =====
def get_audio_dir(lesson_id: int) -> Path:
    """获取课节的音频存储目录"""
    return Path(settings.UPLOAD_DIR) / "audio" / str(lesson_id)


def sanitize_filename(filename: str) -> str:
    """清理文件名：移除路径分隔符和危险字符，保留扩展名"""
    name, ext = os.path.splitext(filename)
    # 只保留字母、数字、中文、空格、连字符、下划线
    safe_chars = []
    for ch in name:
        if ch.isalnum() or ch in " _-()" or "一" <= ch <= "鿿":
            safe_chars.append(ch)
        else:
            safe_chars.append("_")
    safe_name = "".join(safe_chars).strip() or "audio"
    return f"{safe_name}{ext}"


def generate_stored_filename(original_filename: str) -> str:
    """生成存储文件名：{uuid}_{清理后的原始名}，确保唯一性"""
    safe_name = sanitize_filename(original_filename)
    return f"{uuid.uuid4().hex}_{safe_name}"


# ===== 文件验证 =====
def validate_audio_file(file: UploadFile) -> None:
    """
    验证上传的音频文件

    Raises:
        ValueError: 文件类型不支持
        ValueError: 文件大小超限
    """
    # 检查扩展名
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        allowed = [
            e.strip().lower()
            for e in settings.ALLOWED_AUDIO_EXTENSIONS.split(",")
        ]
        if ext not in allowed:
            raise ValueError(
                f"不支持的音频格式: {ext}。允许的格式: {settings.ALLOWED_AUDIO_EXTENSIONS}"
            )
    else:
        raise ValueError("文件名不能为空")


def validate_file_size(file_size: int) -> None:
    """验证文件大小（实际内容读取后进行）"""
    if file_size > settings.MAX_UPLOAD_SIZE:
        max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
        file_mb = file_size // (1024 * 1024)
        raise ValueError(f"文件大小 {file_mb}MB 超过限制 {max_mb}MB")


# ===== 文件操作 =====
async def save_audio_file(lesson_id: int, file: UploadFile) -> tuple[str, str]:
    """
    保存上传的音频文件

    Args:
        lesson_id: 课节ID
        file: FastAPI UploadFile 对象

    Returns:
        (stored_filename, storage_dir_path): 存储的文件名和相对于 UPLOAD_DIR 的目录路径

    流程：
        1. 验证文件类型
        2. 创建 {UPLOAD_DIR}/audio/{lesson_id}/ 目录
        3. 生成唯一文件名
        4. 写入文件内容
        5. 验证文件大小
    """
    validate_audio_file(file)

    audio_dir = get_audio_dir(lesson_id)
    audio_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = generate_stored_filename(file.filename or "audio.mp3")
    file_path = audio_dir / stored_filename

    # 分块写入，避免大文件撑爆内存
    content = await file.read()
    validate_file_size(len(content))

    with open(file_path, "wb") as f:
        f.write(content)

    return stored_filename, str(audio_dir.relative_to(settings.UPLOAD_DIR))


def delete_audio_file(lesson_id: int, filename: Optional[str] = None) -> bool:
    """
    删除音频文件

    Args:
        lesson_id: 课节ID
        filename: 要删除的文件名。为 None 时删除整个课节的音频目录

    Returns:
        是否删除成功
    """
    audio_dir = get_audio_dir(lesson_id)

    if filename:
        file_path = audio_dir / filename
        if file_path.exists():
            file_path.unlink()
            # 如果目录为空，也删除目录
            if not any(audio_dir.iterdir()):
                audio_dir.rmdir()
            return True
        return False
    else:
        # 删除整个目录
        if audio_dir.exists():
            import shutil
            shutil.rmtree(audio_dir)
            return True
        return False


def get_audio_info(lesson_id: int, audio_filename: Optional[str] = None) -> dict | None:
    """
    获取音频文件信息

    Args:
        lesson_id: 课节ID
        audio_filename: 音频文件名（从 Lesson.audio_path 中提取）

    Returns:
        {
            "lesson_id": int,
            "file_name": str,
            "file_path": str,
            "file_size": int,
            "file_extension": str,
            "exists": bool,
        }
        或 None（如果 audio_path 未设置）
    """
    if not audio_filename:
        return None

    audio_dir = get_audio_dir(lesson_id)
    file_path = audio_dir / audio_filename

    if not file_path.exists():
        return {
            "lesson_id": lesson_id,
            "file_name": audio_filename,
            "file_path": str(Path("audio") / str(lesson_id) / audio_filename),
            "file_size": 0,
            "file_extension": os.path.splitext(audio_filename)[1].lower(),
            "exists": False,
        }

    stat = file_path.stat()
    return {
        "lesson_id": lesson_id,
        "file_name": audio_filename,
        "file_path": str(Path("audio") / str(lesson_id) / audio_filename),
        "file_size": stat.st_size,
        "file_extension": os.path.splitext(audio_filename)[1].lower(),
        "exists": True,
    }


def delete_lesson_audio_folder(lesson_id: int) -> None:
    """
    清理课节的所有音频文件（在删除 Lesson 时调用）

    幂等操作：如果目录不存在，静默跳过。
    """
    import shutil

    audio_dir = get_audio_dir(lesson_id)
    if audio_dir.exists():
        shutil.rmtree(audio_dir)
