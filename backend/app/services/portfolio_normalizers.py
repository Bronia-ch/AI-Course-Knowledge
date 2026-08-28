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
    """校验结构化方案，并由后端稳定生成各类 Codex 提示词。"""
    if not isinstance(item, dict):
        raise ValueError("AI 返回的项目执行包格式无效")

    required_text_fields = ("project_brief", "architecture", "directory_structure")
    texts = {
        field: str(item.get(field) or "").strip()[:limit]
        for field, limit in (
            ("project_brief", 6000),
            ("architecture", 5000),
            ("directory_structure", 6000),
        )
    }
    if any(not value for value in texts.values()):
        raise ValueError("AI 返回的项目执行包缺少需求、架构或目录说明")

    technology_choices = record_list(
        item.get("technology_choices"),
        ("name", "purpose", "version_policy"),
        limit=10,
    )
    data_models = record_list(
        item.get("data_models"),
        ("name", "purpose", "fields"),
        limit=12,
    )
    api_contracts = record_list(
        item.get("api_contracts"),
        ("method", "path", "purpose", "request", "response"),
        limit=20,
    )

    phases = []
    for raw_phase in item.get("implementation_phases", [])[:7]:
        if not isinstance(raw_phase, dict):
            continue
        title = str(raw_phase.get("title") or "").strip()
        tasks = string_list(raw_phase.get("tasks"))[:6]
        if not title or not tasks:
            continue
        phases.append({
            "title": title[:200],
            "objective": (
                str(raw_phase.get("objective") or "").strip()[:1000]
                or f"完成{title}并形成可验证结果。"
            ),
            "tasks": tasks,
            "acceptance_criteria": string_list(
                raw_phase.get("acceptance_criteria")
            )[:6] or ["本阶段任务已完成，并通过与风险相匹配的测试。"],
        })
    if not phases:
        raise ValueError("AI 返回的项目执行包没有有效开发阶段")

    normalized = {
        **texts,
        "directory_structure": strip_code_fence(texts["directory_structure"]),
        "technology_choices": technology_choices,
        "data_models": data_models,
        "api_contracts": api_contracts,
        "test_plan": string_list(item.get("test_plan"))[:20],
        "acceptance_checklist": string_list(
            item.get("acceptance_checklist")
        )[:20],
        "readme_requirements": string_list(item.get("readme_requirements"))[:15],
    }
    normalized["implementation_phases"] = [
        {
            **phase,
            "codex_prompt": _build_phase_prompt(
                phase,
                normalized["project_brief"],
            ),
        }
        for phase in phases
    ]
    normalized["codex_master_prompt"] = _build_master_prompt(normalized)
    normalized["review_prompt"] = _build_review_prompt()
    normalized["explanation_prompt"] = _build_explanation_prompt()
    return normalized


def _bullet_text(items: list[str]) -> str:
    """把列表转换为稳定、便于复制的 Markdown 项目符号。"""
    return "\n".join(f"- {item}" for item in items) or "- 无额外要求"


def _build_phase_prompt(phase: dict, project_brief: str) -> str:
    """根据阶段结构生成自包含、长度可控的 Codex 提示词。"""
    return f"""请在当前工作区完成“{phase['title']}”阶段。

项目背景：
{project_brief}

本阶段目标：
{phase['objective']}

需要完成：
{_bullet_text(phase['tasks'])}

验收标准：
{_bullet_text(phase['acceptance_criteria'])}

开始前先阅读工作区中的 AGENTS.md 和需求文档，检查已有代码与依赖，并说明计划和将修改的文件。保护用户已有修改，不使用伪实现冒充完成。完成后运行与本阶段风险相匹配的测试，报告实际结果、修改文件和未验证内容。"""


def _build_master_prompt(package: dict) -> str:
    """根据结构化方案生成完整开发提示词，避免让模型重复输出。"""
    technologies = [
        f"{item.get('name', '')}：{item.get('purpose', '')}；"
        f"版本策略：{item.get('version_policy', '')}"
        for item in package["technology_choices"]
    ]
    phases = []
    for index, phase in enumerate(package["implementation_phases"], start=1):
        phases.append(
            f"{index}. {phase['title']}\n"
            f"   目标：{phase['objective']}\n"
            f"   任务：{'；'.join(phase['tasks'])}\n"
            f"   验收：{'；'.join(phase['acceptance_criteria'])}"
        )
    return f"""请在当前工作区完整实现下面的项目。

开始前必须先阅读 AGENTS.md 及所有需求文档，检查工作区、已有代码、依赖和运行环境；然后说明实施计划和将修改的文件，再分阶段开发。不得删除用户已有修改，不得用伪数据、空函数或静态结果冒充核心功能。

项目需求：
{package['project_brief']}

架构与关键数据流：
{package['architecture']}

技术选择：
{_bullet_text(technologies)}

建议目录结构：
{package['directory_structure']}

实施阶段：
{chr(10).join(phases)}

测试计划：
{_bullet_text(package['test_plan'])}

最终验收：
{_bullet_text(package['acceptance_checklist'])}

完成每个阶段后运行相关测试并报告真实结果。全部完成后给出启动方法、测试结果、已知限制和适合面试的演示顺序。"""


def _build_review_prompt() -> str:
    """生成稳定的项目完成后审查提示词。"""
    return """请先完整阅读当前工作区的需求、架构、实施计划和 AGENTS.md，再基于真实代码执行全面审查。

重点检查：需求是否真实实现；架构、接口和数据模型是否一致；错误处理、边界条件、安全性和资源释放是否可靠；是否存在重复、过度复杂或低效代码；测试是否覆盖核心流程；README 和启动说明是否准确。

先按严重程度列出问题，并给出准确文件位置、影响、证据和建议。不要仅凭设计文档判断完成情况，也不要擅自大规模重写。对用户确认需要修复的问题进行最小范围修改，随后重新运行相关测试并报告结果与未验证内容。"""


def _build_explanation_prompt() -> str:
    """生成面向初学者、同时可支持面试准备的讲解提示词。"""
    return """请完全以当前工作区的真实代码为准，用没有编程基础的人也能理解的方式讲解这个项目。

先用连续的通俗故事说明项目解决什么问题、数据如何从输入走到输出、每个核心模块为什么存在，再给出推荐阅读代码的顺序。随后展示全部人工编写的核心源码，并在对应代码行旁解释作用、输入输出、与其他模块的连接、对应课程知识和初学者容易误解的地方。不要只罗列术语或零碎卡片。

最后补充启动与验证步骤、设计和实际实现的差异、风险与未验证内容，以及面试演示顺序和常见追问。不得虚构不存在的文件、功能、测试或运行结果。"""
