"""规范化并校验 Codex 生成的真实代码分析结果。"""

import json
import re


def normalize_codex_result(data: dict, planned_tasks: list) -> dict:
    texts = {
        field: str(data.get(field) or "").strip()
        for field in (
            "workspace_name",
            "source_fingerprint",
            "implementation_summary",
            "actual_architecture",
            "run_and_test",
        )
    }
    if any(not value for value in texts.values()):
        raise ValueError("Codex 分析缺少工作区、指纹、完成情况、架构或测试说明")
    fingerprint = texts["source_fingerprint"]
    if len(fingerprint) != 64 or any(
        char not in "0123456789abcdef" for char in fingerprint
    ):
        raise ValueError("source_fingerprint 必须是 64 位小写 SHA-256")

    file_tree = paths(data.get("file_tree"), 2000)
    if not file_tree:
        raise ValueError("Codex 分析必须包含真实项目文件清单")
    file_count = nonnegative_int(data.get("file_count"), "file_count")
    if file_count != len(file_tree):
        raise ValueError("file_count 必须与去重后的 file_tree 数量一致")
    source_size = nonnegative_int(data.get("source_size"), "source_size")
    language_stats = normalize_language_stats(data.get("language_stats"))
    key_files = paths(data.get("key_files"), 200)
    if any(path not in file_tree for path in key_files):
        raise ValueError("key_files 包含 file_tree 中不存在的路径")

    key_modules = records(
        data.get("key_modules"), ("path", "responsibility", "evidence"), 50
    )
    execution_flow = strings(data.get("execution_flow"), 40)
    if not key_modules or not execution_flow:
        raise ValueError("Codex 分析必须包含核心模块和执行流程")
    verification_evidence = records(
        data.get("verification_evidence"),
        ("command", "status", "summary", "evidence_files"),
        30,
    )
    if not verification_evidence:
        raise ValueError("Codex 分析必须包含验证证据")
    learning_guide = normalize_learning_guide(data.get("learning_guide"))
    interview_demo = strings(data.get("interview_demo"), 30)
    interview_showcase = normalize_interview_showcase(
        data.get("interview_showcase"),
        texts["implementation_summary"],
        key_modules,
        verification_evidence,
        interview_demo,
    )
    implementation_status = normalize_implementation_status(
        data.get("implementation_status"), planned_tasks
    )
    return {
        **texts,
        "file_count": file_count,
        "source_size": source_size,
        "file_tree": file_tree,
        "language_stats": language_stats,
        "key_files": key_files,
        "key_modules": key_modules,
        "execution_flow": execution_flow,
        "knowledge_mapping": records(
            data.get("knowledge_mapping"),
            ("knowledge_point", "code_locations", "explanation"),
            50,
        ),
        "plan_differences": records(
            data.get("plan_differences"), ("planned", "actual", "impact"), 40
        ),
        "verification_evidence": verification_evidence,
        "interview_demo": interview_demo,
        "interview_questions": records(
            data.get("interview_questions"), ("question", "answer_points"), 30
        ),
        "risks_and_limitations": strings(data.get("risks_and_limitations"), 40),
        "learning_guide": learning_guide,
        "interview_showcase": interview_showcase,
        "implementation_status": implementation_status,
    }


def validate_result_references(
    data: dict, file_tree: list[str], allowed_knowledge: set[str]
) -> None:
    for module in data["key_modules"]:
        if not path_exists(module.get("path", ""), file_tree):
            raise ValueError(
                "核心模块引用了文件清单中不存在的路径："
                f"{module.get('path', '')}"
            )
    for mapping in data["knowledge_mapping"]:
        point = mapping.get("knowledge_point", "")
        if allowed_knowledge and not knowledge_reference_allowed(
            point, allowed_knowledge
        ):
            raise ValueError(f"分析引用了项目未覆盖的课程知识点：{point}")
        _validate_locations(
            mapping.get("code_locations", []),
            file_tree,
            "课程知识映射引用了文件清单中不存在的位置",
        )
    for evidence in data["verification_evidence"]:
        if evidence.get("status") not in {"passed", "failed", "not_run"}:
            raise ValueError("验证证据 status 只能是 passed、failed 或 not_run")
        _validate_locations(
            evidence.get("evidence_files", []),
            file_tree,
            "验证证据引用了文件清单中不存在的文件",
        )
    for section in ("verified_features", "highlights", "technical_challenges"):
        for item in data["interview_showcase"][section]:
            _validate_locations(
                item.get("evidence_files", []),
                file_tree,
                "面试展示内容引用了文件清单中不存在的文件",
            )
    for item in data["implementation_status"].get("task_results", []):
        _validate_locations(
            item.get("evidence_files", []),
            file_tree,
            "任务实现状态引用了文件清单中不存在的文件",
        )
    guide = data["learning_guide"]
    for section in (guide["running_story"], guide["chapters"]):
        for item in section:
            _validate_locations(
                item.get("code_locations", []),
                file_tree,
                "初学者讲解引用了文件清单中不存在的位置",
            )
    for lesson in guide["knowledge_lessons"]:
        _validate_locations(
            lesson.get("code_locations", []),
            file_tree,
            "知识讲解引用了文件清单中不存在的位置",
        )


def _validate_locations(locations: list, file_tree: list[str], message: str) -> None:
    for location in locations:
        if not location_exists(location, file_tree):
            raise ValueError(f"{message}：{location}")


def normalize_learning_guide(value) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Codex 分析必须包含面向初学者的 learning_guide")
    overview = text_record(
        value.get("project_overview"),
        ("one_sentence", "problem_story", "final_result", "learner_goal"),
        "project_overview",
    )
    prerequisites = records(
        value.get("prerequisites"),
        (
            "term",
            "plain_explanation",
            "analogy",
            "project_example",
            "can_ignore_for_now",
        ),
        30,
    )
    running_story = records(
        value.get("running_story"),
        ("step", "user_action", "system_action", "plain_explanation", "code_locations"),
        30,
    )
    chapters = records(
        value.get("chapters"),
        (
            "title",
            "learning_goal",
            "plain_explanation",
            "why_it_matters",
            "analogy",
            "code_locations",
            "focus_points",
            "takeaway",
        ),
        12,
    )
    knowledge_lessons = records(
        value.get("knowledge_lessons"),
        (
            "knowledge_point",
            "what_it_is",
            "why_needed",
            "without_it",
            "project_usage",
            "code_locations",
            "try_it_yourself",
        ),
        50,
    )
    hands_on = records(
        value.get("hands_on"),
        ("title", "action", "command", "expected_result", "what_it_proves"),
        20,
    )
    common = records(
        value.get("common_misunderstandings"), ("question", "plain_answer"), 20
    )
    exercises = records(
        value.get("exercises"),
        ("title", "task", "hint", "expected_learning"),
        20,
    )
    if not prerequisites or len(running_story) < 2 or len(chapters) < 3:
        raise ValueError("learning_guide 必须包含术语准备、完整运行故事和至少 3 个学习章节")
    if not knowledge_lessons or not hands_on or not common or not exercises:
        raise ValueError("learning_guide 缺少知识讲解、动手步骤、常见误解或练习")
    summary_raw = value.get("summary")
    if not isinstance(summary_raw, dict):
        raise ValueError("learning_guide 缺少学习总结")
    summary = {
        "must_remember": strings(summary_raw.get("must_remember"), 20),
        "can_ignore_for_now": strings(summary_raw.get("can_ignore_for_now"), 20),
        "teach_back_prompt": str(summary_raw.get("teach_back_prompt") or "").strip(),
        "self_check_questions": strings(
            summary_raw.get("self_check_questions"), 20
        ),
    }
    if any(not item for item in summary.values()):
        raise ValueError("learning_guide 的学习总结不完整")
    return {
        "project_overview": overview,
        "prerequisites": prerequisites,
        "running_story": running_story,
        "chapters": chapters,
        "knowledge_lessons": knowledge_lessons,
        "hands_on": hands_on,
        "common_misunderstandings": common,
        "exercises": exercises,
        "summary": summary,
    }


def normalize_implementation_status(value, planned_tasks: list) -> dict:
    if not isinstance(value, dict):
        return {"summary": "旧版分析未按计划任务逐项核对。", "task_results": []}
    summary = str(value.get("summary") or "").strip()
    if not summary:
        raise ValueError("implementation_status 缺少整体实现说明")
    tasks_by_title = {task.title.strip(): task for task in planned_tasks}
    raw_results = value.get("task_results")
    if not isinstance(raw_results, list):
        raise ValueError("implementation_status.task_results 必须是数组")
    results = []
    seen_titles = set()
    for raw in raw_results:
        if not isinstance(raw, dict):
            raise ValueError("implementation_status 包含无效任务记录")
        title = str(raw.get("task_title") or "").strip()
        if title not in tasks_by_title:
            raise ValueError(f"implementation_status 引用了未知计划任务：{title}")
        if title in seen_titles:
            raise ValueError(f"implementation_status 重复引用计划任务：{title}")
        status = str(raw.get("status") or "").strip()
        if status not in {"verified", "partial", "not_verified"}:
            raise ValueError(f"任务「{title}」的实现状态无效")
        explanation = str(raw.get("explanation") or "").strip()
        if not explanation:
            raise ValueError(f"任务「{title}」缺少实现状态说明")
        evidence_files = strings(raw.get("evidence_files"), 30)
        if status in {"verified", "partial"} and not evidence_files:
            raise ValueError(f"任务「{title}」标为已实现时必须提供真实代码文件")
        seen_titles.add(title)
        results.append(
            {
                "task_id": tasks_by_title[title].id,
                "task_title": title,
                "status": status,
                "explanation": explanation,
                "evidence_files": evidence_files,
            }
        )
    missing_titles = [title for title in tasks_by_title if title not in seen_titles]
    if missing_titles:
        raise ValueError(
            "implementation_status 未覆盖全部计划任务：" + "、".join(missing_titles)
        )
    return {"summary": summary, "task_results": results}


def normalize_interview_showcase(
    value,
    implementation_summary: str,
    key_modules: list[dict],
    verification_evidence: list[dict],
    interview_demo: list[str],
) -> dict:
    if not isinstance(value, dict):
        return derive_interview_showcase(
            implementation_summary,
            key_modules,
            verification_evidence,
            interview_demo,
        )
    showcase = {
        "headline": str(value.get("headline") or "").strip(),
        "verified_features": records(
            value.get("verified_features"), ("name", "proof", "evidence_files"), 12
        ),
        "highlights": records(
            value.get("highlights"), ("title", "value", "evidence_files"), 10
        ),
        "technical_challenges": records(
            value.get("technical_challenges"),
            ("challenge", "solution", "evidence_files"),
            10,
        ),
        "pitch_30s": str(value.get("pitch_30s") or "").strip(),
        "pitch_2min": str(value.get("pitch_2min") or "").strip(),
    }
    if not showcase["headline"] or not showcase["pitch_30s"] or not showcase["pitch_2min"]:
        raise ValueError("interview_showcase 缺少标题或面试讲述稿")
    if not showcase["verified_features"]:
        raise ValueError("interview_showcase 必须包含真实代码可证明的已验证功能")
    return showcase


def derive_interview_showcase(
    implementation_summary: str,
    key_modules: list[dict],
    verification_evidence: list[dict],
    interview_demo: list[str],
) -> dict:
    runtime_modules = [item for item in key_modules if is_runtime_feature_module(item)]
    features = [
        {
            "name": item.get("responsibility") or item.get("path") or "核心模块",
            "proof": item.get("evidence") or "Codex 已在真实工作区中定位该模块。",
            "evidence_files": [item["path"]] if item.get("path") else [],
        }
        for item in runtime_modules[:8]
    ]
    passed = [item for item in verification_evidence if item.get("status") == "passed"]
    highlights = [
        {
            "title": "真实构建或测试已通过",
            "value": item.get("summary") or item.get("command") or "验证通过",
            "evidence_files": item.get("evidence_files", []),
        }
        for item in passed[:3]
    ]
    pitch_2min = implementation_summary
    if interview_demo:
        pitch_2min += "\n\n演示时可依次介绍：" + "；".join(interview_demo[:6]) + "。"
    return {
        "headline": implementation_summary,
        "verified_features": features,
        "highlights": highlights,
        "technical_challenges": [],
        "pitch_30s": implementation_summary,
        "pitch_2min": pitch_2min,
    }


def is_runtime_feature_module(item: dict) -> bool:
    path = str(item.get("path") or "").strip().replace("\\", "/").lower()
    if not path:
        return False
    parts = path.split("/")
    name = parts[-1]
    if any(part in {"test", "tests", "docs", "documentation"} for part in parts[:-1]):
        return False
    if name.startswith("test_") or name.endswith(
        (".test.js", ".spec.js", ".test.ts", ".spec.ts")
    ):
        return False
    documentation_names = {
        "readme",
        "readme.md",
        "requirements.txt",
        "package.json",
        "package-lock.json",
        "pyproject.toml",
        "poetry.lock",
        "pdm.lock",
        "uv.lock",
        "dockerfile",
        "compose.yaml",
        "docker-compose.yml",
        ".gitignore",
        "license",
        "license.md",
    }
    return name not in documentation_names


def interview_showcase_for_response(analysis, metadata) -> dict:
    stored = json_dict(analysis.interview_showcase)
    if stored:
        return stored
    return derive_interview_showcase(
        analysis.implementation_summary,
        json_records(analysis.key_modules),
        json_records(metadata.verification_evidence),
        json_list(analysis.interview_demo),
    )


def knowledge_reference_allowed(reference: str, allowed_knowledge: set[str]) -> bool:
    normalized_allowed = {
        normalize_knowledge_title(title)
        for title in allowed_knowledge
        if normalize_knowledge_title(title)
    }
    normalized_reference = normalize_knowledge_title(reference)
    if not normalized_reference:
        return False
    if normalized_reference in normalized_allowed:
        return True
    parts = [
        normalize_knowledge_title(part)
        for part in re.split(r"\s*(?:与|和|及|、|\+|/|，|,|；|;)\s*", str(reference))
    ]
    parts = [part for part in parts if part]
    if len(parts) < 2:
        return False
    matched = [
        any(knowledge_part_matches(part, allowed) for allowed in normalized_allowed)
        for part in parts
    ]
    if all(matched):
        return True
    return any(matched) and all(
        is_matched or is_project_implementation_detail(part)
        for part, is_matched in zip(parts, matched)
    )


def knowledge_part_matches(part: str, allowed: str) -> bool:
    if part == allowed:
        return True
    minimum_length = 3 if part.isascii() or allowed.isascii() else 4
    return min(len(part), len(allowed)) >= minimum_length and (
        part in allowed or allowed in part
    )


def normalize_knowledge_title(value: str) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", str(value or "")).lower()


def is_project_implementation_detail(value: str) -> bool:
    if not value or len(value) > 12 or not re.fullmatch(r"[\u4e00-\u9fff]+", value):
        return False
    return value.endswith(
        (
            "处理",
            "逻辑",
            "流程",
            "更新",
            "管理",
            "过滤",
            "转换",
            "初始化",
            "校验",
            "展示",
            "交互",
            "清理",
            "控制",
            "策略",
            "容错",
            "优化",
            "恢复",
            "重试",
            "降级",
            "记录",
        )
    )


def text_record(value, fields: tuple[str, ...], label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"learning_guide 缺少 {label}")
    result = {field: str(value.get(field) or "").strip() for field in fields}
    if any(not item for item in result.values()):
        raise ValueError(f"learning_guide 的 {label} 内容不完整")
    return result


def paths(value, limit: int) -> list[str]:
    result = []
    for raw in value[:limit] if isinstance(value, list) else []:
        path = normalize_reference(raw)
        if not path or path.startswith("../") or "/../" in path or ":" in path:
            raise ValueError(f"文件清单包含不安全的相对路径：{raw}")
        if path not in result:
            result.append(path)
    return result


def path_exists(reference: str, file_tree: list[str]) -> bool:
    normalized = normalize_reference(reference)
    return bool(normalized) and (
        normalized in file_tree
        or any(path.startswith(normalized.rstrip("/") + "/") for path in file_tree)
    )


def location_exists(reference: str, file_tree: list[str]) -> bool:
    normalized = normalize_reference(reference)
    return any(
        normalized == path
        or normalized.startswith(path + ":")
        or normalized.startswith(path + "#")
        for path in file_tree
    )


def normalize_reference(reference: str) -> str:
    normalized = str(reference or "").strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def records(value, fields: tuple[str, ...], limit: int) -> list[dict]:
    if not isinstance(value, list):
        return []
    result = []
    for raw in value[:limit]:
        if not isinstance(raw, dict):
            continue
        result.append(
            {
                field: strings(raw.get(field), 50)
                if isinstance(raw.get(field), list)
                else str(raw.get(field) or "").strip()
                for field in fields
            }
        )
    return result


def strings(value, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value[:limit] if str(item).strip()]


def normalize_language_stats(value) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError("language_stats 必须是语言名称与文件数量的对象")
    result = {}
    for name, count in list(value.items())[:50]:
        clean_name = str(name).strip()
        if clean_name:
            result[clean_name] = nonnegative_int(
                count, f"language_stats.{clean_name}"
            )
    return result


def nonnegative_int(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} 必须是非负整数")
    return value


def json_list(value: str | None) -> list:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def json_records(value: str | None) -> list[dict]:
    return [item for item in json_list(value) if isinstance(item, dict)]


def json_dict(value: str | None) -> dict:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}
