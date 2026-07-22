"""校验并规范化作品相关的 AI 返回内容。"""

import json

from ..models.models import PortfolioOpportunity
from .portfolio_data_utils import (
    parse_string_list,
    record_list,
    string_list,
    strip_code_fence,
)

PROJECT_TYPES = {"micro_demo", "topic_project", "flagship_project"}


def normalize_opportunities(items: list) -> list[dict]:
    """清洗章节作品机会，过滤未知项目类型并限制数量。"""
    normalized = []
    for item in items[:6] if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        project_type = item.get("project_type")
        title = str(item.get("title", "")).strip()
        if not title or project_type not in PROJECT_TYPES:
            continue
        normalized.append({
            "title": title[:200],
            "project_type": project_type,
            "ability_claim": str(item.get("ability_claim", "")).strip(),
            "description": str(item.get("description", "")).strip(),
            "knowledge_points": json.dumps(
                string_list(item.get("knowledge_points")),
                ensure_ascii=False,
            ),
            "core_features": json.dumps(
                string_list(item.get("core_features")),
                ensure_ascii=False,
            ),
            "interview_value": str(item.get("interview_value", "")).strip(),
            "estimated_effort": str(item.get("estimated_effort", "")).strip()[:100],
            "recommended": bool(item.get("recommended", False)),
        })
    return normalized


def normalize_project_blueprint(
    item: dict,
    opportunity: PortfolioOpportunity,
    allowed_knowledge_points: set[str],
) -> dict:
    """清洗正式项目蓝图，并将知识点限制在课程白名单内。"""
    if not isinstance(item, dict):
        raise ValueError("AI 返回的项目蓝图格式无效")

    objective = str(item.get("objective", "")).strip()
    architecture = str(item.get("architecture", "")).strip()
    raw_tasks = item.get("tasks", [])
    if not objective or not architecture or not isinstance(raw_tasks, list):
        raise ValueError("AI 返回的项目蓝图缺少目标、架构或任务")

    tasks = []
    for raw_task in raw_tasks[:8]:
        if not isinstance(raw_task, dict):
            continue
        title = str(raw_task.get("title", "")).strip()
        if not title:
            continue
        tasks.append({
            "title": title[:200],
            "description": str(raw_task.get("description", "")).strip(),
            "acceptance_criteria": str(
                raw_task.get("acceptance_criteria", "")
            ).strip(),
        })
    if not tasks:
        raise ValueError("AI 返回的项目蓝图没有有效任务")

    requested_points = string_list(item.get("knowledge_points"))
    covered_points = [
        point for point in requested_points if point in allowed_knowledge_points
    ]
    if not covered_points:
        covered_points = [
            point
            for point in parse_string_list(opportunity.knowledge_points)
            if point in allowed_knowledge_points
        ]

    return {
        "title": str(item.get("title", "")).strip()[:200] or opportunity.title,
        "project_type": opportunity.project_type,
        "objective": objective,
        "use_case": str(item.get("use_case", "")).strip(),
        "architecture": architecture,
        "technology_stack": json.dumps(
            string_list(item.get("technology_stack")),
            ensure_ascii=False,
        ),
        "core_features": json.dumps(
            string_list(item.get("core_features")),
            ensure_ascii=False,
        ),
        "knowledge_points": json.dumps(covered_points, ensure_ascii=False),
        "deliverables": json.dumps(
            string_list(item.get("deliverables")),
            ensure_ascii=False,
        ),
        "acceptance_criteria": json.dumps(
            string_list(item.get("acceptance_criteria")),
            ensure_ascii=False,
        ),
        "interview_pitch": str(item.get("interview_pitch", "")).strip(),
        "estimated_effort": str(
            item.get("estimated_effort", opportunity.estimated_effort)
        ).strip()[:100],
        "status": "planning",
        "tasks": tasks,
    }


def normalize_execution_package(item: dict) -> dict:
    """校验并限制 AI 执行包的结构和规模。"""
    if not isinstance(item, dict):
        raise ValueError("AI 返回的项目执行包格式无效")

    required_text_fields = (
        "project_brief",
        "architecture",
        "directory_structure",
        "codex_master_prompt",
        "review_prompt",
        "explanation_prompt",
    )
    texts = {
        field: str(item.get(field) or "").strip()
        for field in required_text_fields
    }
    if any(not value for value in texts.values()):
        raise ValueError("AI 返回的项目执行包缺少必要说明或提示词")

    phases = []
    for raw_phase in item.get("implementation_phases", [])[:7]:
        if not isinstance(raw_phase, dict):
            continue
        title = str(raw_phase.get("title") or "").strip()
        prompt = str(raw_phase.get("codex_prompt") or "").strip()
        if not title or not prompt:
            continue
        phases.append({
            "title": title[:200],
            "objective": str(raw_phase.get("objective") or "").strip(),
            "tasks": string_list(raw_phase.get("tasks")),
            "acceptance_criteria": string_list(
                raw_phase.get("acceptance_criteria")
            ),
            "codex_prompt": prompt,
        })
    if not phases:
        raise ValueError("AI 返回的项目执行包没有有效开发阶段")

    return {
        **texts,
        "directory_structure": strip_code_fence(texts["directory_structure"]),
        "technology_choices": record_list(
            item.get("technology_choices"),
            ("name", "purpose", "version_policy"),
            limit=12,
        ),
        "data_models": record_list(
            item.get("data_models"),
            ("name", "purpose", "fields"),
            limit=20,
        ),
        "api_contracts": record_list(
            item.get("api_contracts"),
            ("method", "path", "purpose", "request", "response"),
            limit=30,
        ),
        "implementation_phases": phases,
        "test_plan": string_list(item.get("test_plan"))[:30],
        "acceptance_checklist": string_list(
            item.get("acceptance_checklist")
        )[:30],
        "readme_requirements": string_list(item.get("readme_requirements"))[:20],
    }
