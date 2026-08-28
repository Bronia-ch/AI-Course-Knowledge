"""面试作品机会生成与查询服务。"""

import json

from sqlalchemy.orm import Session, selectinload

from ..ai.deepseek_client import DeepSeekClient
from ..ai.prompts import format_transcript_context
from ..models.models import (
    Chapter,
    KnowledgePoint,
    Lesson,
    PortfolioOpportunity,
    PortfolioProject,
    PortfolioProjectEvidence,
    PortfolioExecutionPackage,
    PortfolioProjectShowcase,
    PortfolioProjectTask,
    Project,
    Transcript,
)
from ..time_utils import utc_now
from .portfolio_formatters import (
    build_portfolio_overview_markdown,
)
from .portfolio_data_utils import (
    normalize_optional_url as _normalize_optional_url,
    parse_json_dict as _parse_json_dict,
    parse_record_list as _parse_record_list,
    parse_string_list as _parse_string_list,
    string_list as _string_list,
)
from .portfolio_normalizers import (
    normalize_execution_package as _normalize_execution_package,
    normalize_opportunities as _normalize_opportunities,
    normalize_project_blueprint as _normalize_project_blueprint,
)
from .portfolio_serializers import (
    opportunity_to_dict,
    portfolio_execution_package_to_dict,
    portfolio_project_to_dict,
)


def _ordered_chapter_lessons(db: Session, chapter_id: int) -> list[Lesson]:
    return (
        db.query(Lesson)
        .filter(Lesson.chapter_id == chapter_id)
        .order_by(Lesson.created_at.asc(), Lesson.id.asc())
        .all()
    )


def _chapter_source_data(
    db: Session,
    chapter_id: int,
) -> tuple[Chapter, list[Lesson], str, list[KnowledgePoint], list[Project]]:
    """读取完整章节并保留课节边界；任一课节不完整时拒绝生成。"""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise ValueError("章节不存在")
    lessons = _ordered_chapter_lessons(db, chapter_id)
    if not lessons:
        raise ValueError("当前章节还没有课节")

    transcript_sections = []
    knowledge_points = []
    course_projects = []
    incomplete = []
    for index, lesson in enumerate(lessons, start=1):
        segments = (
            db.query(Transcript)
            .filter(Transcript.lesson_id == lesson.id)
            .order_by(Transcript.start_time.asc(), Transcript.id.asc())
            .all()
        )
        points = (
            db.query(KnowledgePoint)
            .filter(KnowledgePoint.lesson_id == lesson.id)
            .order_by(KnowledgePoint.timestamp.asc(), KnowledgePoint.id.asc())
            .all()
        )
        if not segments or not points:
            missing = []
            if not segments:
                missing.append("转录")
            if not points:
                missing.append("知识分析")
            incomplete.append(f"{lesson.title}（缺少{'、'.join(missing)}）")
            continue
        transcript_sections.extend([
            f"## 课节 {index}：{lesson.title}",
            format_transcript_context(segments),
        ])
        knowledge_points.extend(points)
        course_projects.extend(
            db.query(Project).filter(Project.lesson_id == lesson.id).all()
        )
    if incomplete:
        raise ValueError("请先完成以下课节：" + "；".join(incomplete))
    return (
        chapter,
        lessons,
        "\n\n".join(transcript_sections),
        knowledge_points,
        course_projects,
    )


def list_portfolio_opportunities(
    db: Session,
    chapter_id: int,
) -> list[PortfolioOpportunity]:
    """查询章节已保存的面试作品机会。"""
    return (
        db.query(PortfolioOpportunity)
        .filter(PortfolioOpportunity.chapter_id == chapter_id)
        .order_by(
            PortfolioOpportunity.recommended.desc(),
            PortfolioOpportunity.id.asc(),
        )
        .all()
    )


def generate_portfolio_opportunities(
    db: Session,
    chapter_id: int,
    client: DeepSeekClient | None = None,
) -> list[PortfolioOpportunity]:
    """按课节顺序聚合完整章节并原子替换作品机会。"""
    chapter, lessons, transcript_text, knowledge_points, course_projects = (
        _chapter_source_data(db, chapter_id)
    )
    knowledge_data = [
        {
            "title": point.title,
            "description": point.description,
            "importance": point.importance,
            "timestamp": point.timestamp,
            "lesson": point.lesson.title,
        }
        for point in knowledge_points
    ]
    project_data = [
        {
            "name": project.name,
            "goal": project.goal,
            "technology_stack": project.technology_stack,
        }
        for project in course_projects
    ]

    ai_client = client or DeepSeekClient()
    generated = ai_client.extract_portfolio_opportunities(
        transcript_text,
        knowledge_data,
        project_data,
    )
    normalized = _normalize_opportunities(generated)
    if not normalized:
        raise ValueError("AI 未生成有效的作品机会")

    try:
        db.query(PortfolioOpportunity).filter(
            PortfolioOpportunity.chapter_id == chapter_id
        ).delete(synchronize_session=False)
        for item in normalized:
            db.add(PortfolioOpportunity(
                lesson_id=lessons[0].id,
                chapter_id=chapter.id,
                **item,
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise

    return list_portfolio_opportunities(db, chapter_id)


def get_portfolio_project(
    db: Session,
    project_id: int,
) -> PortfolioProject | None:
    """查询正式作品项目及任务。"""
    return (
        db.query(PortfolioProject)
        .options(
            selectinload(PortfolioProject.tasks),
            selectinload(PortfolioProject.showcase),
            selectinload(PortfolioProject.evidences).selectinload(
                PortfolioProjectEvidence.task
            ),
            selectinload(PortfolioProject.execution_package),
            selectinload(PortfolioProject.code_analysis),
            selectinload(PortfolioProject.codex_analysis_metadata),
            selectinload(PortfolioProject.concept_guide),
            selectinload(PortfolioProject.chapter).selectinload(Chapter.lessons),
        )
        .filter(PortfolioProject.id == project_id)
        .first()
    )


def get_project_knowledge_points(
    db: Session,
    project: PortfolioProject,
) -> list[KnowledgePoint]:
    """读取作品来源范围内的全部知识点，兼容旧课节项目。"""
    query = db.query(KnowledgePoint)
    if project.chapter_id:
        lesson_ids = [
            item.id for item in _ordered_chapter_lessons(db, project.chapter_id)
        ]
        query = query.filter(KnowledgePoint.lesson_id.in_(lesson_ids))
    else:
        query = query.filter(KnowledgePoint.lesson_id == project.lesson_id)
    return query.order_by(
        KnowledgePoint.lesson_id.asc(),
        KnowledgePoint.timestamp.asc(),
        KnowledgePoint.id.asc(),
    ).all()


def list_portfolio_projects(db: Session) -> list[PortfolioProject]:
    """按最近更新时间查询全部正式作品项目。"""
    return (
        db.query(PortfolioProject)
        .options(
            selectinload(PortfolioProject.tasks),
            selectinload(PortfolioProject.showcase),
            selectinload(PortfolioProject.evidences).selectinload(
                PortfolioProjectEvidence.task
            ),
            selectinload(PortfolioProject.execution_package),
            selectinload(PortfolioProject.code_analysis),
            selectinload(PortfolioProject.codex_analysis_metadata),
            selectinload(PortfolioProject.concept_guide),
            selectinload(PortfolioProject.chapter).selectinload(Chapter.lessons),
        )
        .order_by(PortfolioProject.updated_at.desc(), PortfolioProject.id.desc())
        .all()
    )


def increment_portfolio_learning_count(
    db: Session,
    project_id: int,
) -> PortfolioProject | None:
    """原子累加作品学习次数，并返回最新项目数据。"""
    updated_count = (
        db.query(PortfolioProject)
        .filter(PortfolioProject.id == project_id)
        .update(
            {
                PortfolioProject.learning_count:
                    PortfolioProject.learning_count + 1,
                PortfolioProject.updated_at: utc_now(),
            },
            synchronize_session=False,
        )
    )
    if not updated_count:
        db.rollback()
        return None
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_portfolio_project(db, project_id)


def build_portfolio_overview(db: Session) -> dict:
    """从 Codex 真实分析聚合个人能力作品集，不把计划内容当作完成成果。"""
    projects = list_portfolio_projects(db)
    capability_map = {}
    technology_map = {}
    project_items = []
    analyzed_count = 0
    passed_check_count = 0

    for project in projects:
        project_data = portfolio_project_to_dict(project)
        actual = project_data["implementation_status"]
        analysis = project.code_analysis
        metadata = project.codex_analysis_metadata
        knowledge_mapping = _parse_record_list(analysis.knowledge_mapping) if analysis else []
        verification = _parse_record_list(metadata.verification_evidence) if metadata else []
        passed_checks = [item for item in verification if item.get("status") == "passed"]
        interview_showcase = _parse_json_dict(analysis.interview_showcase) if analysis else {}
        verified_features = interview_showcase.get("verified_features", [])
        if not isinstance(verified_features, list):
            verified_features = []
        if analysis:
            analyzed_count += 1
            passed_check_count += len(passed_checks)

        for mapping in knowledge_mapping:
            name = str(mapping.get("knowledge_point") or "").strip()
            locations = _string_list(mapping.get("code_locations"))
            if not name or not locations:
                continue
            capability = capability_map.setdefault(name, {
                "name": name,
                "status": "partial",
                "projects": [],
                "evidence_locations": [],
            })
            if actual["overall_status"] == "verified":
                capability["status"] = "verified"
            if not any(item["id"] == project.id for item in capability["projects"]):
                capability["projects"].append({"id": project.id, "title": project.title})
            for location in locations:
                if location not in capability["evidence_locations"]:
                    capability["evidence_locations"].append(location)

        for technology in project_data["technology_stack"]:
            item = technology_map.setdefault(technology, {
                "name": technology,
                "project_ids": [],
                "project_count": 0,
            })
            if project.id not in item["project_ids"]:
                item["project_ids"].append(project.id)
                item["project_count"] = len(item["project_ids"])

        headline = str(interview_showcase.get("headline") or "").strip()
        feature_names = [
            str(item.get("name") or "").strip()
            for item in verified_features
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]
        resume_bullets = []
        if analysis:
            resume_bullets.append(
                f"完成「{project.title}」：{headline or analysis.implementation_summary}"
            )
            if feature_names:
                resume_bullets.append("实现：" + "；".join(feature_names[:3]))
            resume_bullets.append(
                f"基于真实代码映射 {len(knowledge_mapping)} 个课程知识点，"
                f"通过 {len(passed_checks)} 项构建或测试检查。"
            )
        project_items.append({
            "id": project.id,
            "title": project.title,
            "objective": project.objective,
            "project_type": project.project_type,
            "analysis_available": bool(analysis),
            "overall_status": actual["overall_status"],
            "completion_percent": actual["completion_percent"],
            "technology_stack": project_data["technology_stack"],
            "verified_feature_count": len(feature_names),
            "knowledge_count": len(knowledge_mapping),
            "passed_check_count": len(passed_checks),
            "headline": headline,
            "resume_bullets": resume_bullets,
            "github_url": project_data["showcase"]["github_url"],
            "demo_url": project_data["showcase"]["demo_url"],
        })

    status_rank = {"verified": 3, "partial": 2, "not_verified": 1, "pending_analysis": 0}
    interview_order = [item for item in project_items if item["analysis_available"]]
    interview_order.sort(
        key=lambda item: (
            status_rank.get(item["overall_status"], 0),
            item["passed_check_count"],
            item["verified_feature_count"],
        ),
        reverse=True,
    )
    for index, item in enumerate(interview_order, start=1):
        item["order"] = index
        item["reason"] = (
            f"包含 {item['verified_feature_count']} 个已识别核心功能、"
            f"{item['passed_check_count']} 项通过检查和 {item['knowledge_count']} 个代码知识映射。"
        )

    capabilities = sorted(
        capability_map.values(),
        key=lambda item: (-len(item["projects"]), item["name"].lower()),
    )
    technologies = sorted(
        technology_map.values(),
        key=lambda item: (-item["project_count"], item["name"].lower()),
    )
    summary = {
        "project_count": len(projects),
        "analyzed_project_count": analyzed_count,
        "verified_project_count": sum(
            item["overall_status"] == "verified" for item in project_items
        ),
        "partial_project_count": sum(
            item["overall_status"] == "partial" for item in project_items
        ),
        "capability_count": len(capabilities),
        "passed_check_count": passed_check_count,
    }
    introduction = (
        f"当前作品集包含 {summary['project_count']} 个课程实践项目，其中 "
        f"{analyzed_count} 个已完成 Codex 真实工作区分析；"
        f"已形成 {len(capabilities)} 项带代码位置的能力映射，并记录 "
        f"{passed_check_count} 项通过的构建或测试检查。"
    )
    overview = {
        "summary": summary,
        "introduction": introduction,
        "capabilities": capabilities,
        "technologies": technologies,
        "projects": project_items,
        "interview_order": interview_order,
    }
    overview["markdown_content"] = build_portfolio_overview_markdown(overview)
    return overview


def update_portfolio_project_task(
    db: Session,
    task_id: int,
    status: str,
) -> PortfolioProject | None:
    """更新任务状态，并根据全部任务同步项目状态。"""
    task = (
        db.query(PortfolioProjectTask)
        .filter(PortfolioProjectTask.id == task_id)
        .first()
    )
    if not task:
        return None

    task.status = status
    project = get_portfolio_project(db, task.project_id)
    statuses = [item.status for item in project.tasks]
    if statuses and all(item == "completed" for item in statuses):
        project.status = "completed"
    elif any(item != "pending" for item in statuses):
        project.status = "in_progress"
    else:
        project.status = "planning"

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_portfolio_project(db, project.id)


def update_portfolio_showcase(
    db: Session,
    project_id: int,
    data: dict,
) -> PortfolioProject | None:
    """创建或更新作品展示资料。"""
    project = get_portfolio_project(db, project_id)
    if not project:
        return None

    github_url = _normalize_optional_url(data.get("github_url"), "GitHub 地址")
    demo_url = _normalize_optional_url(data.get("demo_url"), "演示地址")
    demo_video_url = _normalize_optional_url(data.get("demo_video_url"), "演示视频地址")
    screenshot_urls = [
        _normalize_optional_url(value, "截图地址")
        for value in _string_list(data.get("screenshot_urls"))[:12]
    ]
    showcase = project.showcase or PortfolioProjectShowcase(project_id=project.id)
    showcase.github_url = github_url
    showcase.demo_url = demo_url
    showcase.demo_video_url = demo_video_url
    showcase.screenshot_urls = json.dumps(screenshot_urls, ensure_ascii=False)
    showcase.highlights = json.dumps(
        _string_list(data.get("highlights")),
        ensure_ascii=False,
    )
    showcase.technical_challenges = (
        str(data.get("technical_challenges") or "").strip() or None
    )
    project.updated_at = utc_now()
    db.add(showcase)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_portfolio_project(db, project.id)


def create_portfolio_evidence(
    db: Session,
    project_id: int,
    data: dict,
) -> PortfolioProject | None:
    """为项目新增一条成果证据。"""
    project = get_portfolio_project(db, project_id)
    if not project:
        return None

    title = str(data.get("title") or "").strip()
    if not title:
        raise ValueError("证据标题不能为空")
    task_id = data.get("task_id")
    if task_id is not None and not any(task.id == task_id for task in project.tasks):
        raise ValueError("关联任务不属于当前作品项目")

    evidence = PortfolioProjectEvidence(
        project_id=project.id,
        task_id=task_id,
        evidence_type=data["evidence_type"],
        title=title[:200],
        description=str(data.get("description") or "").strip() or None,
        url=_normalize_optional_url(data.get("url"), "证据链接"),
    )
    project.updated_at = utc_now()
    db.add(evidence)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_portfolio_project(db, project.id)


def delete_portfolio_evidence(
    db: Session,
    evidence_id: int,
) -> bool:
    """删除一条成果证据。"""
    evidence = (
        db.query(PortfolioProjectEvidence)
        .filter(PortfolioProjectEvidence.id == evidence_id)
        .first()
    )
    if not evidence:
        return False
    project = evidence.project
    project.updated_at = utc_now()
    try:
        db.delete(evidence)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True


def get_portfolio_execution_package(
    db: Session,
    project_id: int,
) -> PortfolioExecutionPackage | None:
    """查询作品项目已保存的 AI 执行包。"""
    return (
        db.query(PortfolioExecutionPackage)
        .filter(PortfolioExecutionPackage.project_id == project_id)
        .first()
    )


def generate_portfolio_execution_package(
    db: Session,
    project_id: int,
    client: DeepSeekClient | None = None,
) -> PortfolioExecutionPackage | None:
    """生成或重新生成可交给开发型 AI 的完整项目执行包。"""
    project = get_portfolio_project(db, project_id)
    if not project:
        return None

    points = get_project_knowledge_points(db, project)
    project_data = {
        "title": project.title,
        "project_type": project.project_type,
        "objective": project.objective,
        "use_case": project.use_case,
        "architecture": project.architecture,
        "technology_stack": _parse_string_list(project.technology_stack),
        "core_features": _parse_string_list(project.core_features),
        "knowledge_points": _parse_string_list(project.knowledge_points),
        "deliverables": _parse_string_list(project.deliverables),
        "acceptance_criteria": _parse_string_list(project.acceptance_criteria),
        "estimated_effort": project.estimated_effort,
        "tasks": [
            {
                "title": task.title,
                "description": task.description,
                "acceptance_criteria": task.acceptance_criteria,
            }
            for task in project.tasks
        ],
    }
    point_data = [
        {
            "title": point.title,
            "description": point.description,
            "importance": point.importance,
            "category": point.category,
        }
        for point in points
    ]
    ai_client = client or DeepSeekClient()
    generated = ai_client.create_portfolio_execution_package(
        project_data,
        point_data,
    )
    normalized = _normalize_execution_package(generated)

    package = project.execution_package or PortfolioExecutionPackage(
        project_id=project.id,
    )
    for field in (
        "project_brief",
        "architecture",
        "directory_structure",
        "codex_master_prompt",
        "review_prompt",
        "explanation_prompt",
    ):
        setattr(package, field, normalized[field])
    for field in (
        "technology_choices",
        "data_models",
        "api_contracts",
        "implementation_phases",
        "test_plan",
        "acceptance_checklist",
        "readme_requirements",
    ):
        setattr(
            package,
            field,
            json.dumps(normalized[field], ensure_ascii=False),
        )
    project.updated_at = utc_now()
    db.add(package)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_portfolio_execution_package(db, project.id)


def _get_project_creation_source(
    db: Session,
    opportunity_id: int,
) -> tuple[PortfolioOpportunity, str, list[KnowledgePoint]]:
    opportunity = (
        db.query(PortfolioOpportunity)
        .options(selectinload(PortfolioOpportunity.portfolio_project))
        .filter(PortfolioOpportunity.id == opportunity_id)
        .first()
    )
    if not opportunity:
        raise ValueError("作品机会不存在")

    if opportunity.chapter_id:
        _, _, transcript_text, points, _ = _chapter_source_data(
            db, opportunity.chapter_id
        )
    else:
        segments = (
            db.query(Transcript)
            .filter(Transcript.lesson_id == opportunity.lesson_id)
            .order_by(Transcript.start_time.asc())
            .all()
        )
        points = (
            db.query(KnowledgePoint)
            .filter(KnowledgePoint.lesson_id == opportunity.lesson_id)
            .all()
        )
        if not segments or not points:
            raise ValueError("来源课节缺少转写或知识点数据")
        transcript_text = format_transcript_context(segments)
    return opportunity, transcript_text, points


def _persist_portfolio_project(
    db: Session,
    opportunity: PortfolioOpportunity,
    generated: dict,
    points: list[KnowledgePoint],
) -> PortfolioProject:
    blueprint = _normalize_project_blueprint(
        generated,
        opportunity,
        {point.title for point in points},
    )

    tasks = blueprint.pop("tasks")
    try:
        project = PortfolioProject(
            opportunity_id=opportunity.id,
            lesson_id=opportunity.lesson_id,
            chapter_id=opportunity.chapter_id,
            **blueprint,
        )
        db.add(project)
        db.flush()
        for index, task in enumerate(tasks):
            db.add(PortfolioProjectTask(
                project_id=project.id,
                order_index=index,
                status="pending",
                **task,
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_portfolio_project(db, project.id)


def create_portfolio_project(
    db: Session,
    opportunity_id: int,
    client: DeepSeekClient | None = None,
) -> PortfolioProject:
    """通过 DeepSeek 将作品机会转换为正式项目蓝图。"""
    opportunity, transcript_text, points = _get_project_creation_source(
        db, opportunity_id
    )
    if opportunity.portfolio_project:
        return get_portfolio_project(db, opportunity.portfolio_project.id)

    opportunity_data = opportunity_to_dict(opportunity)
    opportunity_data.pop("portfolio_project_id", None)
    point_data = [
        {
            "title": point.title,
            "description": point.description,
            "importance": point.importance,
        }
        for point in points
    ]
    ai_client = client or DeepSeekClient()
    generated = ai_client.create_portfolio_project_blueprint(
        opportunity_data,
        transcript_text,
        point_data,
    )
    return _persist_portfolio_project(db, opportunity, generated, points)


def import_codex_portfolio_project(
    db: Session,
    opportunity_id: int,
    blueprint: dict,
) -> PortfolioProject:
    """保存 Codex 生成的项目蓝图，全程不调用 DeepSeek。"""
    opportunity, _transcript_text, points = _get_project_creation_source(
        db, opportunity_id
    )
    if opportunity.portfolio_project:
        return get_portfolio_project(db, opportunity.portfolio_project.id)
    return _persist_portfolio_project(db, opportunity, blueprint, points)
