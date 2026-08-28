"""规范化并校验 Codex 生成的真实代码分析结果。"""

import hashlib
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
    learning_guide = normalize_learning_guide(data.get("learning_guide"), file_tree)
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
    status_items = (
        data["implementation_status"].get("task_results", [])
        + data["implementation_status"].get("workflow_results", [])
    )
    for item in status_items:
        _validate_locations(
            item.get("evidence_files", []),
            file_tree,
            "任务实现状态引用了文件清单中不存在的文件",
        )
    guide = data["learning_guide"]
    if guide.get("annotated_files"):
        _validate_locations(
            [guide["code_map"]["entry_point"]],
            file_tree,
            "代码地图引用了不存在的入口文件",
        )
        for section in guide.get("story_sections", []):
            _validate_locations(
                section.get("code_locations", []),
                file_tree,
                "零基础教学章节引用了文件清单中不存在的位置",
            )
    else:
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


def normalize_learning_guide(value, file_tree: list[str] | None = None) -> dict:
    """新版按完整源码批注校验；旧版数据继续兼容展示。"""
    if isinstance(value, dict) and any(
        key in value for key in ("beginner_story", "code_map", "annotated_files")
    ):
        return normalize_annotated_learning_guide(value, file_tree or [])
    return _normalize_legacy_learning_guide(value)


def normalize_annotated_learning_guide(value: dict, file_tree: list[str]) -> dict:
    story_raw = value.get("beginner_story")
    if not isinstance(story_raw, dict):
        raise ValueError("learning_guide 缺少连续的 beginner_story")
    story = text_record(
        story_raw,
        ("title", "content", "after_reading"),
        "beginner_story",
    )
    if len(story["content"]) < 300:
        raise ValueError("beginner_story 过短，无法带零基础读者连续理解项目")
    story["quick_verification"] = text_record(
        story_raw.get("quick_verification"),
        ("action", "command", "expected_result", "what_it_proves"),
        "beginner_story.quick_verification",
    )
    concept_ladder = optional_complete_records(
        value.get("concept_ladder"),
        (
            "term", "before_term", "plain_explanation", "analogy",
            "project_role", "remember",
        ),
        "concept_ladder",
        minimum=3,
        limit=20,
    )
    learning_flow = optional_complete_records(
        value.get("learning_flow"),
        (
            "label", "what_user_sees", "what_program_does", "why_needed",
            "technical_terms",
        ),
        "learning_flow",
        minimum=3,
        limit=10,
    )
    story_sections = optional_complete_records(
        value.get("story_sections"),
        (
            "title", "learning_goal", "content", "new_terms",
            "code_locations", "checkpoint",
        ),
        "story_sections",
        minimum=3,
        limit=12,
    )
    if story_sections and sum(len(item["content"]) for item in story_sections) < 800:
        raise ValueError("story_sections 正文合计过短，无法逐步教会零基础读者")
    self_checks = optional_complete_records(
        value.get("self_checks"),
        ("question", "hint", "answer", "why_it_matters"),
        "self_checks",
        minimum=3,
        limit=12,
    )

    map_raw = value.get("code_map")
    if not isinstance(map_raw, dict):
        raise ValueError("learning_guide 缺少 code_map")
    overview = str(map_raw.get("overview") or "").strip()
    entry_point_raw = str(map_raw.get("entry_point") or "").strip()
    runtime_flow = strings(map_raw.get("runtime_flow"), 40)
    reading_order = records(
        map_raw.get("reading_order"),
        ("path", "role", "why_read_now"),
        200,
    )
    if not overview or not entry_point_raw or len(runtime_flow) < 2 or not reading_order:
        raise ValueError("code_map 必须包含入口、运行流程和阅读顺序")
    reading_paths = []
    for item in reading_order:
        item["path"] = normalize_reference(item["path"])
        if not item["path"] or item["path"] in reading_paths:
            raise ValueError("code_map.reading_order 包含空路径或重复路径")
        reading_paths.append(item["path"])

    inventory_raw = value.get("source_inventory")
    if not isinstance(inventory_raw, list) or len(inventory_raw) > 2000:
        raise ValueError("source_inventory 必须是不超过 2000 项的数组")
    inventory = []
    inventory_by_path = {}
    allowed_categories = {"annotated_source", "supporting_file", "excluded"}
    for raw in inventory_raw:
        if not isinstance(raw, dict):
            raise ValueError("source_inventory 包含无效记录")
        path = normalize_reference(raw.get("path"))
        category = str(raw.get("category") or "").strip()
        reason = str(raw.get("reason") or "").strip()
        if path not in file_tree or path in inventory_by_path:
            raise ValueError(f"source_inventory 引用了未知或重复文件：{path}")
        if category not in allowed_categories or not reason:
            raise ValueError(f"source_inventory 的分类或说明无效：{path}")
        item = {"path": path, "category": category, "reason": reason}
        inventory.append(item)
        inventory_by_path[path] = item
    missing_inventory = [path for path in file_tree if path not in inventory_by_path]
    if missing_inventory:
        raise ValueError(
            "source_inventory 未覆盖全部文件：" + "、".join(missing_inventory[:10])
        )

    files_raw = value.get("annotated_files")
    if not isinstance(files_raw, list) or not files_raw or len(files_raw) > 200:
        raise ValueError("annotated_files 必须包含 1-200 个源码文件")
    annotated_files = []
    annotated_paths = []
    total_source_chars = 0
    for raw in files_raw:
        annotated = normalize_annotated_file(raw, file_tree)
        path = annotated["path"]
        if path in annotated_paths:
            raise ValueError(f"annotated_files 重复包含文件：{path}")
        annotated_paths.append(path)
        total_source_chars += len(annotated["source"])
        if total_source_chars > 2_000_000:
            raise ValueError("annotated_files 的源码文本总量不得超过 2000000 字符")
        annotated_files.append(annotated)

    inventory_annotated = {
        path for path, item in inventory_by_path.items()
        if item["category"] == "annotated_source"
    }
    if set(annotated_paths) != inventory_annotated:
        raise ValueError("annotated_files 必须与 source_inventory 的 annotated_source 完全一致")
    if set(reading_paths) != set(annotated_paths):
        raise ValueError("code_map.reading_order 必须不遗漏地覆盖全部批注源码")
    entry_point = resolve_file_reference(entry_point_raw, annotated_paths)
    if not entry_point:
        raise ValueError(
            "code_map.entry_point 必须引用一个已批注的真实源码文件；"
            f"无法从以下内容识别路径：{entry_point_raw[:200]}"
        )

    return {
        "beginner_story": story,
        "concept_ladder": concept_ladder,
        "learning_flow": learning_flow,
        "story_sections": story_sections,
        "self_checks": self_checks,
        "code_map": {
            "overview": overview,
            "entry_point": entry_point,
            "runtime_flow": runtime_flow,
            "reading_order": reading_order,
        },
        "source_inventory": inventory,
        "annotated_files": annotated_files,
    }


def normalize_annotated_file(value, file_tree: list[str]) -> dict:
    if not isinstance(value, dict):
        raise ValueError("annotated_files 包含无效文件记录")
    path = normalize_reference(value.get("path"))
    role = str(value.get("role") or "").strip()
    language = str(value.get("language") or "").strip()
    source_hash = str(value.get("source_sha256") or "").strip().lower()
    source = value.get("source")
    if path not in file_tree or not role or not language or not isinstance(source, str):
        raise ValueError(f"批注源码的路径、作用、语言或原文无效：{path}")
    if _is_sensitive_source_path(path):
        raise ValueError(f"敏感文件不得写入源码讲解：{path}")
    if not source or len(source) > 200_000:
        raise ValueError(f"源码文件为空或超过 200000 字符：{path}")
    actual_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if source_hash != actual_hash:
        raise ValueError(f"源码 SHA-256 与原文不一致：{path}")

    line_count = len(source.splitlines()) or 1
    raw_annotations = value.get("annotations")
    if not isinstance(raw_annotations, list) or not raw_annotations:
        raise ValueError(f"源码缺少分段批注：{path}")
    annotations = []
    expected_start = 1
    text_fields = (
        "title", "plain_explanation", "why_needed", "input_output",
        "connection", "course_knowledge", "beginner_warning",
    )
    for raw in raw_annotations:
        if not isinstance(raw, dict):
            raise ValueError(f"源码包含无效批注：{path}")
        start = positive_int(raw.get("start_line"), "start_line")
        end = positive_int(raw.get("end_line"), "end_line")
        texts = {field: str(raw.get(field) or "").strip() for field in text_fields}
        if any(not text for text in texts.values()):
            raise ValueError(f"源码批注解释不完整：{path}:{start}-{end}")
        if start != expected_start or end < start or end > line_count:
            raise ValueError(f"源码批注行号必须连续、无重叠且不越界：{path}:{start}-{end}")
        if end - start + 1 > 120:
            raise ValueError(f"单段源码批注不得超过 120 行：{path}:{start}-{end}")
        annotations.append({"start_line": start, "end_line": end, **texts})
        expected_start = end + 1
    if expected_start != line_count + 1:
        raise ValueError(f"源码批注未覆盖到文件最后一行：{path}")
    return {
        "path": path,
        "role": role,
        "language": language,
        "source_sha256": source_hash,
        "source": source,
        "annotations": annotations,
    }


def _is_sensitive_source_path(path: str) -> bool:
    name = path.rsplit("/", 1)[-1].lower()
    return (
        name == ".env"
        or name.startswith(".env.")
        or name in {"id_rsa", "id_ed25519", "credentials.json"}
        or name.endswith((".pem", ".key", ".p12", ".pfx"))
    )


def _normalize_legacy_learning_guide(value) -> dict:
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


def _task_title_key(value: str) -> str:
    """移除 Codex 可能从阶段标题复制的编号前缀，保留真实任务名。"""
    title = str(value or "").strip()
    pattern = re.compile(
        r"^\s*(?:第\s*\d+\s*阶段|阶段\s*\d+)\s*[:：、.\-]\s*"
    )
    while True:
        normalized = pattern.sub("", title, count=1).strip()
        if normalized == title:
            return normalized
        title = normalized


def normalize_implementation_status(value, planned_tasks: list) -> dict:
    if not isinstance(value, dict):
        return {"summary": "旧版分析未按计划任务逐项核对。", "task_results": []}
    summary = str(value.get("summary") or "").strip()
    if not summary:
        raise ValueError("implementation_status 缺少整体实现说明")
    tasks_by_title = {task.title.strip(): task for task in planned_tasks}
    tasks_by_key = {_task_title_key(title): task for title, task in tasks_by_title.items()}
    raw_results = value.get("task_results")
    if not isinstance(raw_results, list):
        raise ValueError("implementation_status.task_results 必须是数组")
    results = []
    workflow_results = []
    seen_titles = set()
    seen_workflow_titles = set()
    for raw in raw_results:
        if not isinstance(raw, dict):
            raise ValueError("implementation_status 包含无效任务记录")
        raw_title = str(raw.get("task_title") or "").strip()
        task = tasks_by_title.get(raw_title) or tasks_by_key.get(
            _task_title_key(raw_title)
        )
        status = str(raw.get("status") or "").strip()
        if status not in {"verified", "partial", "not_verified"}:
            raise ValueError(f"任务「{raw_title}」的实现状态无效")
        explanation = str(raw.get("explanation") or "").strip()
        if not explanation:
            raise ValueError(f"任务「{raw_title}」缺少实现状态说明")
        evidence_files = strings(raw.get("evidence_files"), 30)
        if not task:
            if raw_title in seen_workflow_titles:
                continue
            seen_workflow_titles.add(raw_title)
            workflow_results.append({
                "task_id": None,
                "task_title": raw_title,
                "status": status,
                "explanation": explanation,
                "evidence_files": evidence_files,
            })
            continue

        title = task.title.strip()
        if title in seen_titles:
            raise ValueError(f"implementation_status 重复引用计划任务：{title}")
        if status in {"verified", "partial"} and not evidence_files:
            raise ValueError(f"任务「{title}」标为已实现时必须提供真实代码文件")
        seen_titles.add(title)
        results.append(
            {
                "task_id": task.id,
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
    return {
        "summary": summary,
        "task_results": results,
        "workflow_results": workflow_results,
    }


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


def optional_complete_records(
    value,
    fields: tuple[str, ...],
    label: str,
    minimum: int,
    limit: int,
) -> list[dict]:
    """校验新版教学数组；字段缺失时保留旧版现代 JSON 兼容性。"""
    if value is None:
        return []
    items = records(value, fields, limit)
    if len(items) < minimum:
        raise ValueError(f"learning_guide.{label} 至少需要 {minimum} 项")
    for item in items:
        if any(not item.get(field) for field in fields):
            raise ValueError(f"learning_guide.{label} 包含不完整内容")
    return items


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


def resolve_file_reference(reference: str, candidates: list[str]) -> str:
    """兼容 Codex 把入口路径写进说明句，返回最先提到的真实文件。"""
    normalized = normalize_reference(reference)
    if normalized in candidates:
        return normalized
    lowered = normalized.lower()
    matches = []
    for path in candidates:
        index = lowered.find(path.lower())
        if index >= 0:
            matches.append((index, -len(path), path))
    return min(matches)[2] if matches else ""


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


def positive_int(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} 必须是正整数")
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
