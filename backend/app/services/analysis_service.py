"""DeepSeek 课程知识分析编排；失败时保留上一版可用结果。"""

import json
import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def run_analysis(db_session_factory, lesson_id: int) -> None:
    """先取得完整 AI 结果，再用单一事务替换课节分析数据。"""
    db = db_session_factory()
    try:
        from ..ai.deepseek_client import DeepSeekClient
        from ..ai.prompts import format_transcript_context
        from ..models.models import (
            KnowledgePoint,
            KnowledgeProjectRelation,
            Lesson,
            Project,
            Transcript,
        )

        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            logger.error("分析失败: lesson_id=%d 不存在", lesson_id)
            return
        segments = (
            db.query(Transcript)
            .filter(Transcript.lesson_id == lesson_id)
            .order_by(Transcript.start_time.asc())
            .all()
        )
        if not segments:
            logger.error("分析失败: lesson_id=%d 无转写数据", lesson_id)
            _set_lesson_status(db, lesson_id, "completed")
            return

        transcript_text = format_transcript_context(segments)
        logger.info(
            "DeepSeek 分析开始: lesson_id=%d, transcript_length=%d chars",
            lesson_id,
            len(transcript_text),
        )

        # 所有远程调用先完成。任一步失败时，数据库中的上一版分析保持不变。
        client = DeepSeekClient()
        knowledge_data = client.extract_knowledge_points(transcript_text)
        if not isinstance(knowledge_data, list) or not knowledge_data:
            raise ValueError("DeepSeek 未返回有效知识点")
        project_data = client.extract_projects(transcript_text)
        if not isinstance(project_data, list):
            raise ValueError("DeepSeek 返回的项目结构无效")
        relation_data = client.extract_relations(knowledge_data, project_data)
        if not isinstance(relation_data, list):
            raise ValueError("DeepSeek 返回的知识关联结构无效")

        # 从此处开始的删除和写入只有一次提交，失败会整体回滚。
        db.query(KnowledgeProjectRelation).filter(
            KnowledgeProjectRelation.knowledge_point.has(
                KnowledgePoint.lesson_id == lesson_id
            )
        ).delete(synchronize_session=False)
        deleted_knowledge = db.query(KnowledgePoint).filter(
            KnowledgePoint.lesson_id == lesson_id
        ).delete(synchronize_session=False)
        deleted_projects = db.query(Project).filter(
            Project.lesson_id == lesson_id
        ).delete(synchronize_session=False)

        knowledge_map = {}
        for item in knowledge_data:
            point = KnowledgePoint(
                lesson_id=lesson_id,
                title=str(item.get("title") or "").strip(),
                description=str(item.get("description") or "").strip(),
                importance=item.get("importance", 1),
                category=str(item.get("category") or "").strip(),
                timestamp=item.get("timestamp"),
            )
            if not point.title:
                raise ValueError("DeepSeek 返回了空知识点标题")
            db.add(point)
            db.flush()
            knowledge_map[point.title] = point.id

        project_map = {}
        for item in project_data:
            project = Project(
                lesson_id=lesson_id,
                name=str(item.get("name") or "").strip(),
                goal=str(item.get("goal") or "").strip(),
                input=str(item.get("input") or "").strip(),
                output=str(item.get("output") or "").strip(),
                technology_stack=json.dumps(item.get("technology_stack", []), ensure_ascii=False),
                workflow=json.dumps(item.get("workflow", []), ensure_ascii=False),
            )
            if not project.name:
                raise ValueError("DeepSeek 返回了空项目名称")
            db.add(project)
            db.flush()
            project_map[project.name] = project.id

        saved_relations = 0
        for item in relation_data:
            knowledge_id = knowledge_map.get(item.get("knowledge_point"))
            project_id = project_map.get(item.get("project"))
            if not knowledge_id or not project_id:
                logger.warning(
                    "关联匹配失败: %s -> %s",
                    item.get("knowledge_point"),
                    item.get("project"),
                )
                continue
            db.add(KnowledgeProjectRelation(
                knowledge_point_id=knowledge_id,
                project_id=project_id,
                reason=str(item.get("reason") or "").strip(),
            ))
            saved_relations += 1

        lesson.status = "analyzed"
        db.commit()
        logger.info(
            "分析完成: lesson_id=%d, replaced=%d/%d, knowledge=%d, projects=%d, relations=%d",
            lesson_id,
            deleted_knowledge,
            deleted_projects,
            len(knowledge_data),
            len(project_data),
            saved_relations,
        )
    except ValueError as exc:
        db.rollback()
        logger.error("分析失败（输入或配置错误）: lesson_id=%d, error=%s", lesson_id, exc)
        _restore_completed_status(db, lesson_id)
    except Exception as exc:
        db.rollback()
        logger.exception("分析异常: lesson_id=%d, error=%s", lesson_id, exc)
        _restore_completed_status(db, lesson_id)
    finally:
        db.close()


def _restore_completed_status(db: Session, lesson_id: int) -> None:
    try:
        _set_lesson_status(db, lesson_id, "completed")
    except Exception:
        db.rollback()
        logger.exception("回退 status 失败: lesson_id=%d", lesson_id)


def _set_lesson_status(db: Session, lesson_id: int, status: str) -> None:
    from ..models.models import Lesson

    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if lesson:
        lesson.status = status
        db.commit()
