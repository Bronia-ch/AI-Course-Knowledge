"""使用 DeepSeek 分批重生成作品学习指南，并支持中断后继续。"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

# 允许通过 ``python scripts/regenerate_concept_guides.py`` 从 backend 目录直接运行。
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models.models import PortfolioProject
from app.services.portfolio_learning_service import generate_concept_guide


DEFAULT_STATE_FILE = Path("data/concept-guide-regeneration-state.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="分批重生成作品学习指南")
    parser.add_argument("--limit", type=int, required=True, help="本批最多处理的作品数")
    parser.add_argument("--start-after", type=int, default=0, help="只选择 ID 大于该值的作品")
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help="记录成功与失败结果的本地 JSON 文件",
    )
    return parser.parse_args()


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"selected_ids": [], "completed_ids": [], "failed": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取批处理进度文件：{path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("批处理进度文件格式错误")
    return {
        "selected_ids": [int(item) for item in value.get("selected_ids", [])],
        "completed_ids": [int(item) for item in value.get("completed_ids", [])],
        "failed": {
            str(key): str(message)
            for key, message in dict(value.get("failed", {})).items()
        },
    }


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary_path.replace(path)


def select_project_ids(limit: int, start_after: int) -> list[int]:
    db = SessionLocal()
    try:
        return [
            project_id
            for (project_id,) in (
                db.query(PortfolioProject.id)
                .filter(PortfolioProject.id > start_after)
                .order_by(PortfolioProject.id.asc())
                .limit(limit)
                .all()
            )
        ]
    finally:
        db.close()


def main() -> int:
    raise RuntimeError(
        "DeepSeek 批量重生成已停用。请先运行 audit_concept_guides.py，"
        "再由 Codex 直接生成并导入不合格指南。"
    )
    args = parse_args()
    if args.limit <= 0:
        raise ValueError("--limit 必须大于 0")

    state = load_state(args.state_file)
    if not state["selected_ids"]:
        state["selected_ids"] = select_project_ids(args.limit, args.start_after)
        save_state(args.state_file, state)

    selected = state["selected_ids"]
    completed = set(state["completed_ids"])
    failed = state["failed"]
    logging.info("本批共 %d 个作品，已完成 %d 个", len(selected), len(completed))

    for position, project_id in enumerate(selected, start=1):
        if project_id in completed:
            continue
        db = SessionLocal()
        try:
            generate_concept_guide(db, project_id)
        except Exception as exc:  # 单个作品失败不影响其他作品
            db.rollback()
            failed[str(project_id)] = str(exc)
            logging.exception("生成失败：project_id=%d", project_id)
        else:
            completed.add(project_id)
            state["completed_ids"] = sorted(completed)
            failed.pop(str(project_id), None)
            logging.info("生成完成：%d/%d，project_id=%d", position, len(selected), project_id)
        finally:
            db.close()
            save_state(args.state_file, state)

    logging.info(
        "批处理结束：成功 %d/%d，失败 %d。进度文件：%s",
        len(completed), len(selected), len(failed), args.state_file,
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raise SystemExit(main())
