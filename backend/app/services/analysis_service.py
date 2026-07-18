"""
分析服务 — DeepSeek 知识总结编排

编排流程：
  1. 从 Transcript 表读取并拼接转写文本
  2. 清除旧的 KnowledgePoint 和 Project 记录
  3. 调用 DeepSeek API 提取知识点
  4. 调用 DeepSeek API 识别项目
  5. 写入 KnowledgePoint 和 Project 表
  6. 更新 Lesson.status = "analyzed"

错误处理：
  分析失败时回退 Lesson.status → "completed"（可重试）
"""

import json
import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def run_analysis(
    db_session_factory,
    lesson_id: int,
) -> None:
    """
    后台运行 DeepSeek 知识分析

    此函数作为 FastAPI BackgroundTask 在后台线程中执行。

    Args:
        db_session_factory: SessionLocal（会话工厂）
        lesson_id: 课节ID
    """
    db = db_session_factory()
    try:
        # ---- 1. 获取 Lesson 和 Transcript 数据 ----
        from ..models.models import (
            Lesson,
            Transcript,
            KnowledgePoint,
            Project,
            KnowledgeProjectRelation,
        )
        from ..ai.prompts import format_transcript_context
        from ..ai.deepseek_client import DeepSeekClient

        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            logger.error("分析失败: lesson_id=%d 不存在", lesson_id)
            return

        # 读取转写文本
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
        logger.info("DeepSeek 分析开始: lesson_id=%d, transcript_length=%d chars",
                    lesson_id, len(transcript_text))

        # ---- 2. 清除旧的分析数据 ----
        # 先删除关联关系（bulk delete 不触发 ORM cascade，必须显式处理）
        deleted_rel = (
            db.query(KnowledgeProjectRelation)
            .filter(
                KnowledgeProjectRelation.knowledge_point.has(
                    KnowledgePoint.lesson_id == lesson_id
                )
            )
            .delete(synchronize_session=False)
        )
        if deleted_rel:
            logger.info("已清除 %d 条知识点-项目关联", deleted_rel)

        # 删除旧知识点
        deleted_kp = (
            db.query(KnowledgePoint)
            .filter(KnowledgePoint.lesson_id == lesson_id)
            .delete()
        )

        # 删除旧项目（其关联关系已在上方清除，此处安全）
        deleted_pj = (
            db.query(Project)
            .filter(Project.lesson_id == lesson_id)
            .delete()
        )

        if deleted_kp or deleted_pj:
            logger.info("已清除旧数据: %d 知识点, %d 项目", deleted_kp, deleted_pj)
            db.commit()

        # ---- 3. 创建 DeepSeek 客户端 ----
        client = DeepSeekClient()

        # ---- 4. 提取知识点 ----
        kp_list = client.extract_knowledge_points(transcript_text)
        
        knowledge_point_map = {}

        for kp_data in kp_list:
            kp = KnowledgePoint(
                lesson_id=lesson_id,
                title=kp_data.get("title", ""),
                description=kp_data.get("description", ""),
                importance=kp_data.get("importance", 1),
                category=kp_data.get("category", ""),
                timestamp=kp_data.get("timestamp", None),
            )
            db.add(kp)
            db.flush()

            knowledge_point_map[kp.title] = kp.id

        db.commit()

        logger.info("知识点提取完成: %d 个知识点", len(kp_list))

        # ---- 5. 识别项目 ----
        pj_list = client.extract_projects(transcript_text)
        
        project_map = {}

        for pj_data in pj_list:
            pj = Project(
                lesson_id=lesson_id,
                name=pj_data.get("name",""),
                goal=pj_data.get("goal",""),
                input=pj_data.get("input",""),
                output=pj_data.get("output",""),
                technology_stack=json.dumps(
                    pj_data.get("technology_stack",[]),
                    ensure_ascii=False
                ),
                workflow=json.dumps(
                    pj_data.get("workflow",[]),
                    ensure_ascii=False
                ),
            )

            db.add(pj)
            db.flush()

            project_map[pj.name] = pj.id

        db.commit()

        logger.info("项目识别完成: %d 个项目", len(pj_list))


        # ---- 6. 分析知识点-项目关联 ----
        relations = client.extract_relations(
            kp_list,
            pj_list,
        )

        for rel in relations:

            kp_id = knowledge_point_map.get(
                rel.get("knowledge_point")
            )

            pj_id = project_map.get(
                rel.get("project")
            )

            # 找不到对应知识点或项目时跳过
            if not kp_id or not pj_id:
                logger.warning(
                    "关联匹配失败: %s -> %s",
                    rel.get("knowledge_point"),
                    rel.get("project"),
                )
                continue


            db.add(
                KnowledgeProjectRelation(
                    knowledge_point_id=kp_id,
                    project_id=pj_id,
                    reason=rel.get("reason", ""),
                )
            )

        db.commit()

        logger.info(
            "知识点-项目关联完成: %d 条",
            len(relations)
        )


        # ---- 7. 更新状态 ----
        _set_lesson_status(db, lesson_id, "analyzed")
        logger.info("分析完成: lesson_id=%d", lesson_id)

    except ValueError as e:
        # API Key 未配置等配置错误
        logger.error("分析失败（配置错误）: lesson_id=%d, error=%s", lesson_id, e)
        try:
            _set_lesson_status(db, lesson_id, "completed")
        except Exception:
            pass
    except Exception as e:
        logger.exception("分析异常: lesson_id=%d, error=%s", lesson_id, e)
        try:
            _set_lesson_status(db, lesson_id, "completed")
        except Exception:
            logger.exception("回退 status 失败")
    finally:
        db.close()


def _set_lesson_status(db: Session, lesson_id: int, status: str) -> None:
    """更新 Lesson 状态"""
    from ..models.models import Lesson
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if lesson:
        lesson.status = status
        db.commit()
