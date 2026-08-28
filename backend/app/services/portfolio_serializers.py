"""将作品 ORM 模型转换为稳定的 API 响应结构。"""

from ..models.models import (
    PortfolioExecutionPackage,
    PortfolioOpportunity,
    PortfolioProject,
)
from .portfolio_data_utils import (
    parse_json_dict,
    parse_record_list,
    parse_string_list,
)
from .portfolio_formatters import (
    build_codex_final_return_prompt,
    build_execution_package_markdown,
)


def opportunity_to_dict(opportunity: PortfolioOpportunity) -> dict:
    """将作品机会转换为 API 响应，兼容章节和旧课节来源。"""
    return {
        "id": opportunity.id,
        "lesson_id": opportunity.lesson_id,
        "chapter_id": opportunity.chapter_id,
        "source_scope": "chapter" if opportunity.chapter_id else "lesson",
        "covered_lessons": [
            {"id": lesson.id, "title": lesson.title}
            for lesson in sorted(
                opportunity.chapter.lessons,
                key=lambda item: (item.created_at, item.id),
            )
        ] if opportunity.chapter else [
            {"id": opportunity.lesson.id, "title": opportunity.lesson.title}
        ],
        "title": opportunity.title,
        "project_type": opportunity.project_type,
        "ability_claim": opportunity.ability_claim,
        "description": opportunity.description,
        "knowledge_points": parse_string_list(opportunity.knowledge_points),
        "core_features": parse_string_list(opportunity.core_features),
        "interview_value": opportunity.interview_value,
        "estimated_effort": opportunity.estimated_effort,
        "recommended": opportunity.recommended,
        "created_at": opportunity.created_at,
        "portfolio_project_id": opportunity.portfolio_project.id
        if opportunity.portfolio_project
        else None,
        "learning_count": int(opportunity.portfolio_project.learning_count or 0)
        if opportunity.portfolio_project
        else 0,
    }


def portfolio_execution_package_to_dict(
    package: PortfolioExecutionPackage,
) -> dict:
    """将执行包转换为 API 响应，并补全 Codex 收尾流程。"""
    final_return_prompt = build_codex_final_return_prompt(package.project_id)
    master_prompt = package.codex_master_prompt.rstrip()
    if "portfolio_analysis_result.json" not in master_prompt:
        master_prompt = f"{master_prompt}\n\n{final_return_prompt}"
    phases = parse_record_list(package.implementation_phases)
    if not any(
        "portfolio_analysis_result.json" in str(item.get("codex_prompt") or "")
        for item in phases
    ):
        phases.append({
            "title": "最终验收与 JSON 回传",
            "objective": "在用户确认项目可用后，由 Codex 基于真实工作区生成知识库需要的最终分析文件。",
            "tasks": [
                "执行代码审查并修复确认的问题",
                "完成项目讲解并等待用户最终验收",
                "读取分析任务与 JSON Schema",
                "检查真实源码和测试并生成 portfolio_analysis_result.json",
            ],
            "acceptance_criteria": [
                "用户已经明确确认项目验收通过",
                "portfolio_analysis_result.json 位于项目根目录",
                "文件可以被标准 JSON 解析器读取",
                "测试结果和未验证内容均如实记录",
            ],
            "codex_prompt": final_return_prompt,
        })
    data = {
        "id": package.id,
        "project_id": package.project_id,
        "project_brief": package.project_brief,
        "technology_choices": parse_record_list(package.technology_choices),
        "architecture": package.architecture,
        "directory_structure": package.directory_structure,
        "data_models": parse_record_list(package.data_models),
        "api_contracts": parse_record_list(package.api_contracts),
        "implementation_phases": phases,
        "test_plan": parse_string_list(package.test_plan),
        "acceptance_checklist": parse_string_list(package.acceptance_checklist),
        "readme_requirements": parse_string_list(package.readme_requirements),
        "codex_master_prompt": master_prompt,
        "review_prompt": package.review_prompt,
        "explanation_prompt": package.explanation_prompt,
        "created_at": package.created_at,
        "updated_at": package.updated_at,
    }
    data["markdown_content"] = build_execution_package_markdown(data)
    return data


def project_implementation_status(project: PortfolioProject) -> dict:
    """优先返回 Codex 对真实实现的核对状态，并兼容旧版分析。"""
    analysis = project.code_analysis
    if not analysis:
        return {
            "analysis_available": False,
            "overall_status": "pending_analysis",
            "summary": "尚未回传 Codex 真实代码分析。",
            "completion_percent": 0,
            "verified_task_count": 0,
            "partial_task_count": 0,
            "task_results": [],
            "legacy_derived": False,
        }

    stored = parse_json_dict(analysis.implementation_status)
    valid_task_ids = {task.id for task in project.tasks}
    task_results = []
    seen_ids = set()
    for raw in stored.get("task_results", []):
        if not isinstance(raw, dict):
            continue
        task_id = raw.get("task_id")
        status = raw.get("status")
        if task_id not in valid_task_ids or task_id in seen_ids:
            continue
        if status not in {"verified", "partial", "not_verified"}:
            continue
        seen_ids.add(task_id)
        task_results.append(raw)

    if task_results:
        verified_count = sum(item["status"] == "verified" for item in task_results)
        partial_count = sum(item["status"] == "partial" for item in task_results)
        total = len(project.tasks) or len(task_results)
        completion = round((verified_count + partial_count * 0.5) / total * 100)
        if total and verified_count == total:
            overall = "verified"
        elif verified_count or partial_count:
            overall = "partial"
        else:
            overall = "not_verified"
        return {
            "analysis_available": True,
            "overall_status": overall,
            "summary": str(stored.get("summary") or "Codex 已逐项核对计划任务。"),
            "completion_percent": completion,
            "verified_task_count": verified_count,
            "partial_task_count": partial_count,
            "task_results": task_results,
            "legacy_derived": False,
        }

    module_count = len(parse_record_list(analysis.key_modules))
    evidence_count = (
        len(parse_record_list(project.codex_analysis_metadata.verification_evidence))
        if project.codex_analysis_metadata
        else 0
    )
    estimated_items = min(
        len(project.tasks),
        max(module_count, 1 if evidence_count else 0),
    )
    completion = (
        round(estimated_items / len(project.tasks) * 100)
        if project.tasks
        else 0
    )
    has_real_analysis = bool(module_count or evidence_count)
    return {
        "analysis_available": True,
        "overall_status": "partial" if has_real_analysis else "not_verified",
        "summary": (
            "这是旧版分析生成的保守进度；真实代码和测试已存在，但尚未按计划任务逐项核对。"
            if has_real_analysis else "Codex 分析尚未提供可确认的实现证据。"
        ),
        "completion_percent": completion,
        "verified_task_count": 0,
        "partial_task_count": estimated_items if has_real_analysis else 0,
        "task_results": [],
        "legacy_derived": True,
    }


def portfolio_project_to_dict(project: PortfolioProject) -> dict:
    """将正式作品项目转换为 API 响应。"""
    task_count = len(project.tasks)
    completed_task_count = sum(
        task.status == "completed" for task in project.tasks
    )
    showcase = project.showcase
    implementation_status = project_implementation_status(project)
    effective_status = {
        "verified": "completed",
        "partial": "in_progress",
        "not_verified": "in_progress",
    }.get(implementation_status["overall_status"], project.status)
    evidence_types = {evidence.evidence_type for evidence in project.evidences}
    completeness_checks = [
        (project.status == "completed", "完成全部开发任务"),
        (bool(showcase and showcase.github_url), "补充 GitHub 源码地址"),
        (bool(showcase and showcase.demo_url), "补充在线演示地址"),
        (bool(showcase and parse_string_list(showcase.highlights)), "填写项目亮点"),
        (bool(showcase and showcase.technical_challenges), "填写技术难点与解决方案"),
        ("test" in evidence_types, "添加测试结果证据"),
        ("document" in evidence_types, "添加项目文档证据"),
    ]
    completed_item_count = sum(completed for completed, _ in completeness_checks)
    return {
        "id": project.id,
        "opportunity_id": project.opportunity_id,
        "lesson_id": project.lesson_id,
        "chapter_id": project.chapter_id,
        "chapter_title": project.chapter.title if project.chapter else None,
        "course_id": project.chapter.course_id if project.chapter else None,
        "covered_lessons": [
            {"id": lesson.id, "title": lesson.title}
            for lesson in sorted(
                project.chapter.lessons,
                key=lambda item: (item.created_at, item.id),
            )
        ] if project.chapter else [],
        "title": project.title,
        "project_type": project.project_type,
        "objective": project.objective,
        "use_case": project.use_case,
        "architecture": project.architecture,
        "technology_stack": parse_string_list(project.technology_stack),
        "core_features": parse_string_list(project.core_features),
        "knowledge_points": parse_string_list(project.knowledge_points),
        "deliverables": parse_string_list(project.deliverables),
        "acceptance_criteria": parse_string_list(project.acceptance_criteria),
        "interview_pitch": project.interview_pitch,
        "estimated_effort": project.estimated_effort,
        "status": effective_status,
        "learning_count": int(project.learning_count or 0),
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "task_count": task_count,
        "completed_task_count": completed_task_count,
        "progress_percent": round(
            completed_task_count / task_count * 100,
            1,
        ) if task_count else 0.0,
        "implementation_status": implementation_status,
        "concept_guide_available": getattr(project, "concept_guide", None) is not None,
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "acceptance_criteria": task.acceptance_criteria,
                "order_index": task.order_index,
                "status": task.status,
            }
            for task in project.tasks
        ],
        "showcase": {
            "id": showcase.id if showcase else None,
            "github_url": showcase.github_url if showcase else None,
            "demo_url": showcase.demo_url if showcase else None,
            "demo_video_url": showcase.demo_video_url if showcase else None,
            "screenshot_urls": parse_string_list(showcase.screenshot_urls) if showcase else [],
            "highlights": parse_string_list(showcase.highlights) if showcase else [],
            "technical_challenges": showcase.technical_challenges if showcase else None,
            "updated_at": showcase.updated_at if showcase else None,
        },
        "evidences": [
            {
                "id": evidence.id,
                "evidence_type": evidence.evidence_type,
                "title": evidence.title,
                "description": evidence.description,
                "url": evidence.url,
                "task_id": evidence.task_id,
                "task_title": evidence.task.title if evidence.task else None,
                "created_at": evidence.created_at,
            }
            for evidence in project.evidences
        ],
        "completeness": {
            "score": round(completed_item_count / len(completeness_checks) * 100),
            "completed_item_count": completed_item_count,
            "total_item_count": len(completeness_checks),
            "missing_items": [
                label for completed, label in completeness_checks if not completed
            ],
        },
    }
