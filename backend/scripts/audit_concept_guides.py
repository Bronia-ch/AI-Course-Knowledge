"""审查作品学习指南是否符合零基础详细讲解标准。"""

from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models.models import PortfolioConceptGuide, PortfolioProject


REPORT_PATH = Path("data/concept-guide-audit.json")


def guide_issues(content: object) -> list[str]:
    """返回不满足页面教学标准的原因；不读取或修改任何外部服务。"""
    if not isinstance(content, dict):
        return ["指南内容不是 JSON 对象"]
    issues: list[str] = []
    story = content.get("beginner_story")
    if not isinstance(story, dict):
        issues.append("缺少开篇故事")
    else:
        text = str(story.get("content") or "").strip()
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
        if len(text) < 650:
            issues.append("开篇少于 650 字")
        if len(paragraphs) < 4:
            issues.append("开篇少于 4 段")

    concepts = content.get("concept_ladder")
    if not isinstance(concepts, list) or len(concepts) < 8:
        issues.append("概念卡少于 8 个")
    else:
        for field, label in (("analogy", "类比"), ("project_role", "项目例子")):
            values = {
                str(item.get(field) or "").strip()
                for item in concepts if isinstance(item, dict)
            }
            if len(values) < (len(concepts) * 3 + 3) // 4:
                issues.append(f"概念卡{label}重复过多")

    sections = content.get("story_sections")
    if not isinstance(sections, list) or len(sections) < 5:
        issues.append("连续教学章节少于 5 节")
    else:
        total = sum(
            len(str(item.get("content") or ""))
            for item in sections if isinstance(item, dict)
        )
        if total < 800:
            issues.append("连续教学章节少于 800 字")
    return issues


def main() -> None:
    db = SessionLocal()
    try:
        rows = (
            db.query(PortfolioProject.id, PortfolioProject.title, PortfolioConceptGuide.content)
            .outerjoin(PortfolioConceptGuide)
            .order_by(PortfolioProject.id.asc())
            .all()
        )
    finally:
        db.close()

    failures = []
    for project_id, title, raw_content in rows:
        try:
            content = json.loads(raw_content) if raw_content else None
        except json.JSONDecodeError:
            content = None
        issues = guide_issues(content)
        if issues:
            failures.append({"project_id": project_id, "title": title, "issues": issues})

    report = {
        "total_projects": len(rows),
        "qualified_count": len(rows) - len(failures),
        "unqualified_count": len(failures),
        "unqualified_projects": failures,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "total_projects": report["total_projects"],
        "qualified_count": report["qualified_count"],
        "unqualified_count": report["unqualified_count"],
        "first_unqualified": failures[:10],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
