"""作品总览、执行包和 Codex 收尾提示词的纯文本格式化。"""


def build_portfolio_overview_markdown(data: dict) -> str:
    """将作品总览数据转换为便于复制的 Markdown。"""
    lines = [
        "# 个人技术作品集",
        "",
        data["introduction"],
        "",
        "## 已验证能力",
        "",
    ]
    if data["capabilities"]:
        for item in data["capabilities"]:
            projects = "、".join(project["title"] for project in item["projects"])
            evidence = "、".join(item["evidence_locations"][:5])
            lines.append(
                f"- **{item['name']}**（{item['status']}）："
                f"{projects}；代码位置：{evidence}"
            )
    else:
        lines.append("- 尚无已回传的真实代码能力映射。")
    lines.extend(["", "## 代表项目", ""])
    for project in data["interview_order"]:
        lines.extend([
            f"### {project['order']}. {project['title']}",
            "",
            project["headline"] or project["objective"],
            "",
            *[f"- {bullet}" for bullet in project["resume_bullets"]],
            "",
        ])
    lines.extend(["## 项目中使用的技术", ""])
    lines.extend(
        f"- {item['name']}：用于 {item['project_count']} 个项目"
        for item in data["technologies"]
    )
    return "\n".join(lines)


def build_codex_final_return_prompt(project_id: int) -> str:
    """生成交给 Codex 的最终验收与 JSON 回传要求。"""
    return f"""## 强制收尾流程：最终验收与 JSON 回传

完成全部开发阶段后，不要把“代码已经写完”视为任务结束。必须按以下顺序收尾：

1. 读取并执行 `CODE_REVIEW_PROMPT.md`，检查真实代码并修复确认的问题。
2. 重新运行与风险相匹配的构建和测试，报告真实结果。
3. 读取并执行 `PROJECT_EXPLANATION_PROMPT.md`，基于实际实现完成项目讲解。
4. 请求用户进行最终操作验收，并等待用户明确回复验收通过。
5. 用户确认验收通过后，读取 `CODEX_ANALYSIS_REQUEST.md` 和 `ANALYSIS_RESULT_SCHEMA.json`。
6. 全面检查当前真实工作区，严格按照 Schema 在项目根目录生成 `portfolio_analysis_result.json`。
7. `project_id` 必须填写 `{project_id}`；不得伪造文件、功能、测试结果或代码位置。
8. 使用标准 JSON 解析器验证文件后，告诉用户文件路径、已执行的测试和尚未验证的内容。

最终任务只有在 `portfolio_analysis_result.json` 已生成并通过 JSON 解析校验后才算完成。"""


def build_execution_package_markdown(data: dict) -> str:
    """组合便于复制、保存和交给其他 AI 的执行包 Markdown。"""
    lines = [
        "# AI 项目执行包",
        "",
        f"生成时间：{data['updated_at'].isoformat(timespec='seconds')}",
        "",
        "## 项目需求",
        "",
        data["project_brief"],
        "",
        "## 技术选择",
        "",
    ]
    for technology in data["technology_choices"]:
        lines.append(
            f"- **{technology.get('name', '')}**：{technology.get('purpose', '')} "
            f"版本策略：{technology.get('version_policy', '')}"
        )
    lines.extend([
        "",
        "## 系统架构",
        "",
        data["architecture"],
        "",
        "## 建议目录结构",
        "",
        "```text",
        data["directory_structure"],
        "```",
        "",
        "## 数据模型",
        "",
    ])
    for model in data["data_models"]:
        fields = model.get("fields", [])
        field_text = "；".join(fields) if isinstance(fields, list) else str(fields)
        lines.append(
            f"- **{model.get('name', '')}**：{model.get('purpose', '')}。{field_text}"
        )
    lines.extend(["", "## API 设计", ""])
    for api in data["api_contracts"]:
        lines.append(
            f"- `{api.get('method', '')} {api.get('path', '')}`："
            f"{api.get('purpose', '')}；请求：{api.get('request', '')}；"
            f"响应：{api.get('response', '')}"
        )
    lines.extend(["", "## 分阶段实施", ""])
    for index, phase in enumerate(data["implementation_phases"], start=1):
        lines.extend([
            f"### 阶段 {index}：{phase.get('title', '')}",
            "",
            phase.get("objective", ""),
            "",
            *[f"- {task}" for task in phase.get("tasks", [])],
            "",
            "验收标准：",
            *[f"- {item}" for item in phase.get("acceptance_criteria", [])],
            "",
            "阶段 Codex 提示词：",
            "",
            phase.get("codex_prompt", ""),
            "",
        ])
    for title, key in (
        ("测试计划", "test_plan"),
        ("最终验收清单", "acceptance_checklist"),
        ("README 要求", "readme_requirements"),
    ):
        lines.extend([f"## {title}", ""])
        lines.extend(f"- {item}" for item in data[key])
        lines.append("")
    lines.extend([
        "## Codex 完整开发提示词",
        "",
        data["codex_master_prompt"],
        "",
        "## 完成后代码审查提示词",
        "",
        data["review_prompt"],
        "",
        "## 项目讲解提示词",
        "",
        data["explanation_prompt"],
        "",
    ])
    return "\n".join(lines)
