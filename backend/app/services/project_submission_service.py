"""完成项目 ZIP 的安全扫描与非公开保存；不调用或执行任何 AI。"""

import hashlib
import io
import json
import stat
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from uuid import uuid4

from sqlalchemy.orm import Session

from ..models.models import (
    PortfolioCodeAnalysis,
    PortfolioCodexAnalysisMetadata,
    PortfolioProjectSubmission,
)
from .portfolio_service import get_portfolio_project
from ..time_utils import utc_now

MAX_ARCHIVE_SIZE = 20 * 1024 * 1024
MAX_FILE_COUNT = 2000
MAX_UNCOMPRESSED_SIZE = 100 * 1024 * 1024
MAX_SOURCE_FILE_SIZE = 512 * 1024
MAX_TREE_FILES = MAX_FILE_COUNT

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_STORAGE_ROOT = BACKEND_DIR / "data" / "portfolio_submissions"

IGNORED_PARTS = {
    ".git", ".idea", ".vscode", "node_modules", "venv", ".venv",
    "env", "__pycache__", ".pytest_cache", ".mypy_cache", ".next",
    "dist", "build", "coverage", ".coverage", "target", "vendor",
}
TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".php", ".rb", ".swift",
    ".kt", ".kts", ".sql", ".html", ".css", ".scss", ".less",
    ".vue", ".svelte", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".md", ".txt", ".sh", ".ps1", ".bat", ".xml",
    ".graphql", ".proto", ".env.example",
}
TEXT_FILENAMES = {
    "dockerfile", "makefile", "procfile", "gemfile", "rakefile",
    "requirements.txt", "pyproject.toml", "package.json", "readme.md",
    "cargo.toml", "go.mod", "pom.xml", "build.gradle", "compose.yaml",
    "docker-compose.yml", ".gitignore", ".env.example",
}
LANGUAGE_NAMES = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript/JSX",
    ".ts": "TypeScript", ".tsx": "TypeScript/TSX", ".java": "Java",
    ".go": "Go", ".rs": "Rust", ".c": "C", ".cpp": "C++",
    ".cs": "C#", ".php": "PHP", ".rb": "Ruby", ".swift": "Swift",
    ".kt": "Kotlin", ".sql": "SQL", ".html": "HTML", ".css": "CSS",
    ".vue": "Vue", ".svelte": "Svelte", ".md": "Markdown",
}


def get_project_submission(
    db: Session,
    project_id: int,
) -> PortfolioProjectSubmission | None:
    return (
        db.query(PortfolioProjectSubmission)
        .filter(PortfolioProjectSubmission.project_id == project_id)
        .first()
    )


def save_project_submission(
    db: Session,
    project_id: int,
    original_filename: str,
    archive_bytes: bytes,
    storage_root: Path | None = None,
) -> PortfolioProjectSubmission | None:
    """安全扫描并保存源码归档；上传新版本时使旧分析失效。"""
    project = get_portfolio_project(db, project_id)
    if not project:
        return None
    scan = scan_source_archive(original_filename, archive_bytes)
    fingerprint = scan["source_fingerprint"]

    target_root = (storage_root or DEFAULT_STORAGE_ROOT).resolve()
    project_dir = target_root / str(project.id)
    project_dir.mkdir(parents=True, exist_ok=True)
    new_archive_path = project_dir / f"{uuid4().hex}.zip"
    new_archive_path.write_bytes(archive_bytes)

    submission = get_project_submission(db, project.id) or PortfolioProjectSubmission(
        project_id=project.id
    )
    source_changed = submission.source_fingerprint != fingerprint
    old_archive_path = Path(submission.archive_path) if submission.archive_path else None
    submission.original_filename = Path(original_filename).name[:255]
    submission.archive_path = str(new_archive_path)
    submission.source_fingerprint = fingerprint
    submission.file_count = scan["file_count"]
    submission.source_size = scan["source_size"]
    submission.file_tree = json.dumps(scan["file_tree"], ensure_ascii=False)
    submission.language_stats = json.dumps(scan["language_stats"], ensure_ascii=False)
    submission.key_files = json.dumps(scan["key_files"], ensure_ascii=False)
    submission.updated_at = utc_now()
    project.updated_at = utc_now()

    old_analysis = (
        db.query(PortfolioCodeAnalysis)
        .filter(PortfolioCodeAnalysis.project_id == project.id)
        .first()
    )
    old_metadata = (
        db.query(PortfolioCodexAnalysisMetadata)
        .filter(PortfolioCodexAnalysisMetadata.project_id == project.id)
        .first()
    )
    if old_analysis and source_changed:
        db.delete(old_analysis)
    elif old_analysis:
        old_analysis.original_filename = submission.original_filename
        old_analysis.archive_path = submission.archive_path
        old_analysis.file_count = submission.file_count
        old_analysis.source_size = submission.source_size
        old_analysis.file_tree = submission.file_tree
        old_analysis.language_stats = submission.language_stats
        old_analysis.key_files = submission.key_files
    if old_metadata and source_changed:
        db.delete(old_metadata)
    db.add(submission)
    try:
        db.commit()
    except Exception:
        db.rollback()
        new_archive_path.unlink(missing_ok=True)
        raise

    if old_archive_path and old_archive_path != new_archive_path:
        try:
            if old_archive_path.resolve().is_relative_to(target_root):
                old_archive_path.unlink(missing_ok=True)
        except OSError:
            pass
    return get_project_submission(db, project.id)


def scan_source_archive(original_filename: str, archive_bytes: bytes) -> dict:
    """只扫描受支持文本元数据，不解压或执行 ZIP 中的文件。"""
    if not original_filename.lower().endswith(".zip"):
        raise ValueError("仅支持 ZIP 格式的完成项目")
    if not archive_bytes:
        raise ValueError("上传的项目 ZIP 为空")
    if len(archive_bytes) > MAX_ARCHIVE_SIZE:
        raise ValueError("项目 ZIP 不能超过 20 MB")
    if not zipfile.is_zipfile(io.BytesIO(archive_bytes)):
        raise ValueError("上传文件不是有效的 ZIP")

    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            all_infos = archive.infolist()
            if len(all_infos) > MAX_FILE_COUNT:
                raise ValueError("ZIP 条目数量超过 2000 个")
            infos = [info for info in all_infos if not info.is_dir()]
            if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_SIZE:
                raise ValueError("ZIP 解压后总大小超过 100 MB")

            validated = [(_validate_archive_path(info), info) for info in infos]
            root_name = _common_wrapper_root([path for path, _ in validated])
            safe_infos = []
            seen_paths = set()
            for raw_path, info in validated:
                normalized_path = _remove_wrapper_root(raw_path, root_name)
                path_key = normalized_path.lower()
                if path_key in seen_paths:
                    raise ValueError("ZIP 中存在重复文件路径")
                seen_paths.add(path_key)
                if not _is_ignored_path(normalized_path):
                    safe_infos.append((normalized_path, info))

            file_tree = [path for path, _ in safe_infos[:MAX_TREE_FILES]]
            fingerprint_hasher = hashlib.sha256()
            for path, info in sorted(safe_infos, key=lambda item: item[0].lower()):
                fingerprint_hasher.update(path.encode("utf-8"))
                fingerprint_hasher.update(b"\x00")
                fingerprint_hasher.update(hashlib.sha256(archive.read(info)).digest())
            source_candidates = [
                (path, info)
                for path, info in safe_infos
                if _is_text_source(path) and info.file_size <= MAX_SOURCE_FILE_SIZE
            ]
            language_stats = Counter(
                _language_name(path) for path, _ in source_candidates
            )
            source_candidates.sort(key=lambda item: _source_priority(item[0]))
            key_files = []
            source_size = 0
            for path, info in source_candidates:
                raw = archive.read(info)
                if b"\x00" in raw[:4096]:
                    continue
                key_files.append(path)
                source_size += info.file_size
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError("无法安全读取项目 ZIP") from exc

    if not key_files:
        raise ValueError("ZIP 中没有可识别的源代码或文本文件")
    return {
        "file_count": len(source_candidates),
        "source_size": source_size,
        "file_tree": file_tree,
        "language_stats": dict(language_stats),
        "key_files": key_files,
        "source_fingerprint": fingerprint_hasher.hexdigest(),
    }


def submission_to_dict(submission: PortfolioProjectSubmission) -> dict:
    return {
        "id": submission.id,
        "project_id": submission.project_id,
        "original_filename": submission.original_filename,
        "source_fingerprint": submission.source_fingerprint,
        "file_count": submission.file_count,
        "source_size": submission.source_size,
        "file_tree": _json_list(submission.file_tree),
        "language_stats": _json_dict(submission.language_stats),
        "key_files": _json_list(submission.key_files),
        "created_at": submission.created_at,
        "updated_at": submission.updated_at,
    }


def _validate_archive_path(info: zipfile.ZipInfo) -> str:
    name = info.filename.replace("\\", "/")
    if not name or "\x00" in name or name.startswith("/"):
        raise ValueError("ZIP 包含不安全的绝对路径")
    path = PurePosixPath(name)
    if ".." in path.parts or any(":" in part for part in path.parts):
        raise ValueError("ZIP 包含路径穿越或盘符路径")
    mode = info.external_attr >> 16
    if mode and stat.S_ISLNK(mode):
        raise ValueError("ZIP 不允许包含符号链接")
    if info.flag_bits & 0x1:
        raise ValueError("ZIP 不允许包含加密文件")
    return path.as_posix()


def _common_wrapper_root(paths: list[str]) -> str | None:
    if not paths or any(len(PurePosixPath(path).parts) < 2 for path in paths):
        return None
    first_parts = {PurePosixPath(path).parts[0] for path in paths}
    return next(iter(first_parts)) if len(first_parts) == 1 else None


def _remove_wrapper_root(path: str, root_name: str | None) -> str:
    parts = PurePosixPath(path).parts
    return PurePosixPath(*parts[1:]).as_posix() if root_name else path


def _is_ignored_path(path: str) -> bool:
    return any(part.lower() in IGNORED_PARTS for part in PurePosixPath(path).parts)


def _is_text_source(path: str) -> bool:
    pure_path = PurePosixPath(path)
    name = pure_path.name.lower()
    suffixes = "".join(pure_path.suffixes[-2:]).lower()
    return (
        name in TEXT_FILENAMES
        or pure_path.suffix.lower() in TEXT_EXTENSIONS
        or suffixes in TEXT_EXTENSIONS
    )


def _language_name(path: str) -> str:
    return LANGUAGE_NAMES.get(PurePosixPath(path).suffix.lower(), "Config/Docs")


def _source_priority(path: str) -> tuple:
    pure_path = PurePosixPath(path)
    name = pure_path.name.lower()
    if name in TEXT_FILENAMES:
        priority = 0
    elif name.startswith(("main.", "app.", "index.", "server.", "manage.")):
        priority = 1
    elif "test" in name or "tests" in (part.lower() for part in pure_path.parts):
        priority = 3
    else:
        priority = 2
    return priority, len(pure_path.parts), path.lower()


def _json_list(value: str | None) -> list:
    try:
        result = json.loads(value or "[]")
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _json_dict(value: str | None) -> dict[str, int]:
    try:
        result = json.loads(value or "{}")
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}
