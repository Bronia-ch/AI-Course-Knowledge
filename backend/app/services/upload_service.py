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
from io import BytesIO
from pathlib import Path
from typing import Optional

import av
from fastapi import UploadFile

from ..config import settings


BACKEND_DIR = Path(__file__).resolve().parents[2]
UPLOAD_CHUNK_SIZE = 1024 * 1024


# ===== 路径工具 =====
def get_upload_root() -> Path:
    """返回与应用启动目录无关的上传根目录。"""
    root = Path(settings.UPLOAD_DIR)
    return root.resolve() if root.is_absolute() else (BACKEND_DIR / root).resolve()


def get_audio_dir(lesson_id: int) -> Path:
    """获取课节的音频存储目录"""
    return get_upload_root() / "audio" / str(lesson_id)


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


def generate_stored_filename(
    original_filename: str,
    normalized_extension: str | None = None,
) -> str:
    """生成存储文件名：{uuid}_{清理后的原始名}，确保唯一性"""
    safe_name = sanitize_filename(original_filename)
    if normalized_extension:
        safe_name = f"{Path(safe_name).stem}{normalized_extension}"
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


def _inspect_audio_source(source) -> tuple[str, str]:
    """检测真实音频格式，返回规范扩展名和 MIME 类型。"""
    try:
        with av.open(source) as container:
            if not any(stream.type == "audio" for stream in container.streams):
                raise ValueError("文件中未检测到音频轨道")
            if any(stream.type == "video" for stream in container.streams):
                raise ValueError("不支持包含视频轨道的文件")
            format_names = set(container.format.name.split(","))
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("无法识别音频文件的真实格式") from exc

    format_mapping = (
        ({"mp3"}, (".mp3", "audio/mpeg")),
        ({"wav"}, (".wav", "audio/wav")),
        ({"mov", "mp4", "m4a", "3gp", "3g2", "mj2"}, (".m4a", "audio/mp4")),
        ({"ogg"}, (".ogg", "audio/ogg")),
        ({"flac"}, (".flac", "audio/flac")),
        ({"aac"}, (".aac", "audio/aac")),
        ({"asf"}, (".wma", "audio/x-ms-wma")),
    )
    for known_formats, result in format_mapping:
        if format_names & known_formats:
            return result

    raise ValueError(f"不支持的音频容器格式: {','.join(sorted(format_names))}")


def inspect_audio_content(content: bytes) -> tuple[str, str]:
    """兼容字节输入的真实音频检测。"""
    return _inspect_audio_source(BytesIO(content))


def inspect_audio_path(path: Path) -> tuple[str, str]:
    """直接检查磁盘文件，避免把大音频整体载入内存。"""
    return _inspect_audio_source(str(path))


def get_media_type(filename: str) -> str:
    """根据已规范化的文件扩展名返回 MIME 类型。"""
    media_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
        ".wma": "audio/x-ms-wma",
    }
    return media_types.get(Path(filename).suffix.lower(), "application/octet-stream")


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

    temp_path = audio_dir / f".{uuid.uuid4().hex}.upload"
    total_size = 0
    try:
        with open(temp_path, "wb") as output:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                total_size += len(chunk)
                validate_file_size(total_size)
                output.write(chunk)
        if total_size == 0:
            raise ValueError("上传的音频文件为空")

        normalized_extension, _ = inspect_audio_path(temp_path)
        stored_filename = generate_stored_filename(
            file.filename or "audio.mp3",
            normalized_extension,
        )
        file_path = audio_dir / stored_filename
        temp_path.replace(file_path)
        return stored_filename, str(audio_dir.relative_to(get_upload_root()))
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


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
            "file_path": (Path("audio") / str(lesson_id) / audio_filename).as_posix(),
            "file_size": 0,
            "file_extension": os.path.splitext(audio_filename)[1].lower(),
            "media_type": get_media_type(audio_filename),
            "exists": False,
        }

    stat = file_path.stat()
    return {
        "lesson_id": lesson_id,
        "file_name": audio_filename,
        "file_path": (Path("audio") / str(lesson_id) / audio_filename).as_posix(),
        "file_size": stat.st_size,
        "file_extension": os.path.splitext(audio_filename)[1].lower(),
        "media_type": get_media_type(audio_filename),
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
