"""按课程批量重写作品学习指南的开篇故事，不调用外部模型。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models.models import Chapter, PortfolioConceptGuide, PortfolioProject
from app.time_utils import utc_now


def _scenario(title: str, stack: list[str]) -> tuple[str, str, str]:
    text = f"{title} {' '.join(stack)}".lower()
    if any(word in text for word in ("rnn", "lstm", "序列", "股票", "时间")):
        return ("一段按时间排列的数据", "前面发生的内容", "后面的变化")
    if any(word in text for word in ("transformer", "文本", "新闻", "bert", "语言")):
        return ("一句按顺序写出的文本", "前面的词语", "后面的词语")
    if any(word in text for word in ("dataloader", "数据集", "标注")):
        return ("一张带着正确标签的图片", "图片内容", "正确标签")
    return ("一张需要判断内容的图片", "局部边缘、纹理和位置", "最终类别")


def build_opening(project: PortfolioProject) -> dict:
    title = project.title
    objective = project.objective.strip()
    try:
        stack = json.loads(project.technology_stack)
    except json.JSONDecodeError:
        stack = []
    sample, first_clue, result = _scenario(title, stack if isinstance(stack, list) else [])
    story = "\n\n".join([
        f"先想象把{sample}交给这个作品。人往往能凭经验立刻做出判断，"
        f"但程序最初只会读取整理后的数字和位置关系。以《{title}》为例，"
        f"它的目标是：{objective}。开篇先不背术语，而是跟着这一份具体输入，"
        "观察信息怎样一步步变成可解释的判断。",
        f"第一步，程序不会直接宣布答案，而是把输入整理成可计算、又不丢失顺序或位置的表示。"
        f"它需要从中寻找{first_clue}，而不是把所有细节混成一团。"
        "这好比先在一张线索图上标出值得注意的位置：后续步骤才知道应该比较什么，"
        "也能避免仅凭表面数字做出仓促结论。",
        "第二步，作品会按自身的处理规则逐步组合这些线索：有的项目比较局部图像特征，"
        "有的项目保留时间顺序，有的项目理解文本前后关系。关键不是记住一个模型名称，"
        "而是理解每一层处理都在回答同一个问题：这一份输入里，哪些证据支持当前判断，"
        "哪些证据仍然不够。最后得到的不是绝对真相，而是关于" + result + "的一个可检查结果。",
        "最后必须用没有参与学习或调参的资料进行检查，并回看容易出错的样本。"
        "如果结果变好，还要确认不是因为多看了答案、换了更容易的数据或只挑选了有利案例。"
        "因此，这个作品的学习重点是：先用具体输入理解处理过程，再用独立验证确认结论边界；"
        "没有真实运行日志时，不把任何假设数值当成当前项目已经达到的成绩。"
        "学完后可以挑一份新的输入，按“输入是什么、程序先看什么、如何组合线索、怎样检查”四个问题复述全过程；"
        "能说清这四件事，就已经真正掌握了作品要表达的思路。",
    ])
    return {
        "title": f"跟着{sample}，从第一条线索看到《{title}》怎样得出结果",
        "content": story,
        "after_reading": "能用自己的话说明输入怎样被处理、为什么需要这些步骤，以及怎样验证结果是否可信。",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--course-id", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        guides = (
            db.query(PortfolioProject, PortfolioConceptGuide)
            .join(Chapter, PortfolioProject.chapter_id == Chapter.id)
            .join(PortfolioConceptGuide, PortfolioConceptGuide.project_id == PortfolioProject.id)
            .filter(Chapter.course_id == args.course_id)
            .order_by(PortfolioProject.id.asc())
            .all()
        )
        preview = []
        backup = {}
        for project, guide in guides:
            content = json.loads(guide.content)
            preview.append({"project_id": project.id, "title": project.title, "opening": build_opening(project)})
            backup[str(project.id)] = content
            if args.apply:
                content["beginner_story"] = build_opening(project)
                guide.content = json.dumps(content, ensure_ascii=False)
                guide.updated_at = utc_now()
        if args.apply:
            backup_path = Path(f"data/concept-guide-opening-backup-course-{args.course_id}.json")
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            if not backup_path.exists():
                backup_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")
            db.commit()
        print(json.dumps({"count": len(preview), "applied": args.apply, "preview": preview[:3]}, ensure_ascii=False, indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
