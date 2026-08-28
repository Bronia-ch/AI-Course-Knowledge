"""将 AI 项目执行包导出为可直接交给 Codex 的 ZIP。"""

import io
import json
import zipfile

from sqlalchemy.orm import Session

from .codex_analysis_service import analysis_request, analysis_result_schema
from .portfolio_service import (
    get_portfolio_execution_package,
    get_project_knowledge_points,
    get_portfolio_project,
    portfolio_execution_package_to_dict,
)


HANDOFF_FILES = (
    "START_HERE.md",
    "AGENTS.md",
    "PROJECT_SPEC.md",
    "ARCHITECTURE.md",
    "IMPLEMENTATION_PLAN.md",
    "TEST_AND_ACCEPTANCE.md",
    "COURSE_KNOWLEDGE.md",
    "CODEX_MASTER_PROMPT.md",
    "CODE_REVIEW_PROMPT.md",
    "PROJECT_EXPLANATION_PROMPT.md",
    "CODEX_ANALYSIS_REQUEST.md",
    "ANALYSIS_RESULT_SCHEMA.json",
    "README_REQUIREMENTS.md",
)


def build_codex_handoff_archive(db: Session, project_id: int) -> bytes:
    """构建内存 ZIP；不会在服务器磁盘生成临时文件。"""
    project = get_portfolio_project(db, project_id)
    if not project:
        raise LookupError("作品项目不存在")
    package = get_portfolio_execution_package(db, project_id)
    if not package:
        raise ValueError("请先生成 AI 项目执行包")

    package_data = portfolio_execution_package_to_dict(package)
    knowledge_points = get_project_knowledge_points(db, project)
    files = _build_handoff_files(project, package_data, knowledge_points)

    archive = io.BytesIO()
    with zipfile.ZipFile(
        archive,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zip_file:
        for filename in HANDOFF_FILES:
            zip_file.writestr(filename, files[filename].encode("utf-8"))
        zip_file.writestr(
            "handoff_manifest.json",
            json.dumps(
                {
                    "format_version": "1.2",
                    "project_id": project.id,
                    "project_title": project.title,
                    "generated_at": package.updated_at.isoformat(),
                    "files": list(HANDOFF_FILES),
                },
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8"),
        )
    return archive.getvalue()


def _build_handoff_files(project, package: dict, knowledge_points: list) -> dict:
    task_titles = [task.title.strip() for task in project.tasks]
    start_prompt = (
        "请先完整阅读 START_HERE.md、AGENTS.md、PROJECT_SPEC.md、"
        "ARCHITECTURE.md、IMPLEMENTATION_PLAN.md 和 TEST_AND_ACCEPTANCE.md。"
        "先检查当前工作区与可用环境，说明实施计划和将修改的文件；"
        "确认约束后分阶段完成项目、运行测试并报告结果。"
    )
    return {
        "START_HERE.md": _start_here(project.title, start_prompt),
        "AGENTS.md": _agents_instructions(),
        "PROJECT_SPEC.md": _project_spec(project.title, package),
        "ARCHITECTURE.md": _architecture(package),
        "IMPLEMENTATION_PLAN.md": _implementation_plan(project, package),
        "TEST_AND_ACCEPTANCE.md": _test_and_acceptance(package),
        "COURSE_KNOWLEDGE.md": _course_knowledge(project, knowledge_points),
        "CODEX_MASTER_PROMPT.md": _document(
            "Codex 完整开发提示词",
            package["codex_master_prompt"],
        ),
        "CODE_REVIEW_PROMPT.md": _document(
            "项目完成后的代码审查提示词",
            package["review_prompt"],
        ),
        "PROJECT_EXPLANATION_PROMPT.md": _document(
            "项目讲解提示词",
            package["explanation_prompt"],
        ),
        "CODEX_ANALYSIS_REQUEST.md": analysis_request(project.id, task_titles),
        "ANALYSIS_RESULT_SCHEMA.json": json.dumps(
            analysis_result_schema(project.id, task_titles),
            ensure_ascii=False,
            indent=2,
        ),
        "README_REQUIREMENTS.md": _list_document(
            "README 编写要求",
            package["readme_requirements"],
        ),
    }


def _start_here(title: str, start_prompt: str) -> str:
    return f"""# {title} — Codex 开发交付包

这个目录包含完成项目所需的需求、架构、任务、测试和课程知识背景。

## 使用步骤

1. 将整个 ZIP 解压到一个新的项目目录。
2. 使用 Codex 打开这个目录。
3. 把下面的“启动指令”发送给 Codex。
4. 审核 Codex 给出的计划，然后让它按 `IMPLEMENTATION_PLAN.md` 分阶段实施。
5. 每个阶段结束后检查测试结果，不要只接受文字形式的“已完成”。
6. 项目完成后依次使用 `CODE_REVIEW_PROMPT.md` 和 `PROJECT_EXPLANATION_PROMPT.md`。
7. 用户验收通过后，阅读 `CODEX_ANALYSIS_REQUEST.md` 和 `ANALYSIS_RESULT_SCHEMA.json`，检查真实工作区并生成 `portfolio_analysis_result.json`。
8. 将 `portfolio_analysis_result.json` 交给用户上传回课程知识库，不需要压缩或上传项目源码。

## 启动指令

{start_prompt}

如果希望 Codex 一次理解全部目标，也可以直接发送 `CODEX_MASTER_PROMPT.md` 的内容。
"""


def _agents_instructions() -> str:
    return """# AGENTS.md

请始终使用中文与用户沟通。

这是一个用于面试展示的独立项目。开发时必须遵守：

1. 开始修改前，先阅读本目录全部 `.md` 需求和约束文件。
2. 先检查工作区现状、已有代码、依赖和运行环境，再给出实施计划。
3. 文件名和变量名使用英文；注释可使用中文。
4. 分阶段实现，每个阶段都运行与风险相匹配的测试。
5. 不得用伪数据、空函数或静态页面冒充已完成的核心功能。
6. 不得删除或覆盖用户已有修改；发现冲突时先说明。
7. 技术版本以实施时的官方稳定版本和现有环境为准，不要凭记忆声称“最新版”。
8. 保持项目范围与 `PROJECT_SPEC.md` 一致，避免无意义的过度设计。
9. 完成后提供启动命令、测试结果、已知限制和面试演示步骤。
10. 讲解必须基于实际代码；如果实现与设计文档有差异，要明确指出。
11. 用户验收通过后，必须执行 `CODEX_ANALYSIS_REQUEST.md`，并在项目根目录生成可被标准 JSON 解析器读取的 `portfolio_analysis_result.json`。
"""


def _project_spec(title: str, package: dict) -> str:
    return f"""# {title} — 项目需求

{package['project_brief']}
"""


def _architecture(package: dict) -> str:
    lines = ["# 技术架构", "", "## 技术选择", ""]
    for item in package["technology_choices"]:
        lines.extend([
            f"### {item.get('name', '')}",
            "",
            item.get("purpose", ""),
            "",
            f"版本策略：{item.get('version_policy', '')}",
            "",
        ])
    lines.extend([
        "## 系统架构与数据流",
        "",
        package["architecture"],
        "",
        "## 建议目录结构",
        "",
        "```text",
        package["directory_structure"],
        "```",
        "",
        "## 数据模型",
        "",
    ])
    for model in package["data_models"]:
        fields = model.get("fields", [])
        lines.extend([
            f"### {model.get('name', '')}",
            "",
            model.get("purpose", ""),
            "",
            *[f"- {field}" for field in fields if isinstance(fields, list)],
            "",
        ])
    lines.extend(["## API 契约", ""])
    for api in package["api_contracts"]:
        lines.extend([
            f"### `{api.get('method', '')} {api.get('path', '')}`",
            "",
            api.get("purpose", ""),
            "",
            f"- 请求：{api.get('request', '')}",
            f"- 响应：{api.get('response', '')}",
            "",
        ])
    return "\n".join(lines)


def _implementation_plan(project, package: dict) -> str:
    lines = [
        "# 分阶段实施计划",
        "",
        "## JSON 回传任务名称",
        "",
        "生成 `portfolio_analysis_result.json` 时，"
        "`implementation_status.task_results[].task_title` "
        "必须逐字使用下列名称，不要添加“阶段 1”等前缀：",
        "",
        *[f"- `{task.title.strip()}`" for task in project.tasks],
        "",
    ]
    for index, phase in enumerate(package["implementation_phases"], start=1):
        lines.extend([
            f"## 阶段 {index}：{phase.get('title', '')}",
            "",
            phase.get("objective", ""),
            "",
            "### 开发任务",
            "",
            *[f"- {task}" for task in phase.get("tasks", [])],
            "",
            "### 验收标准",
            "",
            *[f"- {item}" for item in phase.get("acceptance_criteria", [])],
            "",
            "### 可直接发送给 Codex 的阶段提示词",
            "",
            phase.get("codex_prompt", ""),
            "",
        ])
    return "\n".join(lines)


def _test_and_acceptance(package: dict) -> str:
    return "\n".join([
        "# 测试与验收",
        "",
        "## 测试计划",
        "",
        *[f"- {item}" for item in package["test_plan"]],
        "",
        "## 最终验收清单",
        "",
        *[f"- [ ] {item}" for item in package["acceptance_checklist"]],
        "",
    ])


def _course_knowledge(project, knowledge_points: list) -> str:
    lines = [
        "# 课程知识背景",
        "",
        "这些内容用于帮助开发型 AI 理解项目需要证明的课程能力，不代表可以脱离真实代码声称已经掌握。",
        "",
    ]
    try:
        covered_data = json.loads(project.knowledge_points or "[]")
        covered_titles = set(covered_data) if isinstance(covered_data, list) else set()
    except (json.JSONDecodeError, TypeError):
        covered_titles = set()
    for point in knowledge_points:
        if covered_titles and point.title not in covered_titles:
            continue
        lines.extend([
            f"## {point.title}",
            "",
            point.description or "课程未提供详细说明。",
            "",
            f"- 重要程度：{point.importance}/5",
            f"- 分类：{point.category or '未分类'}",
            f"- 来源课节：{point.lesson.title}",
            "",
        ])
    return "\n".join(lines)


def _document(title: str, content: str) -> str:
    return f"# {title}\n\n{content}\n"


def _list_document(title: str, items: list[str]) -> str:
    return "\n".join([f"# {title}", "", *[f"- {item}" for item in items], ""])
