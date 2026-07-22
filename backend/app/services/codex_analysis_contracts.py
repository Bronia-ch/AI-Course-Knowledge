"""Codex 真实代码分析任务说明与 JSON Schema 契约。"""


def analysis_request(project_id: int) -> str:
    """生成随项目执行包交付的最终分析说明。"""
    return f"""# Codex 真实代码分析与回传任务

完成项目开发、用户验收、代码审查和项目讲解后，在当前项目根目录执行本任务。

1. 阅读 `PROJECT_SPEC.md`、`ARCHITECTURE.md`、`IMPLEMENTATION_PLAN.md`、`COURSE_KNOWLEDGE.md` 和 `ANALYSIS_RESULT_SCHEMA.json`。
2. 全面检查当前工作区的真实源码、配置、测试和文档，不得只根据计划文件推测。
3. 识别真实语言、入口、核心模块、执行流程、启动方式和测试方式。
4. 运行安全且与项目匹配的构建和测试；不得伪造测试结果。未运行的检查必须标为 `not_run`。
5. 所有模块、知识映射和证据必须引用 `file_tree` 中真实存在的相对路径。
6. 忽略 `.git`、`node_modules`、虚拟环境、构建产物和缓存目录，将其余文件路径规范为 `/` 分隔的相对路径并排序去重后写入 `file_tree`；`file_count` 等于该数组长度，`source_size` 等于这些文件的字节数之和。
7. 计算 `source_fingerprint`：按 `file_tree` 顺序，对每个文件依次向 SHA-256 写入 UTF-8 路径、一个零字节和该文件内容的 SHA-256 二进制摘要，最终输出 64 位小写十六进制摘要。
8. 严格按照 JSON Schema 在项目根目录生成 `portfolio_analysis_result.json`，不要添加 Markdown 标记。
9. `project_id` 必须填写 `{project_id}`，不得修改。
10. `learning_guide` 面向第一次接触该技术的初学者，不是技术审计报告。必须形成一条连续的教学路线，而不是互不相关的摘要卡片。
11. 专业术语第一次出现时必须提供大白话解释、生活类比和当前项目中的例子；不要用另一个未解释的术语解释它。
12. `knowledge_mapping[].knowledge_point` 必须以 `COURSE_KNOWLEDGE.md` 的原始标题为基础；可以组合多个课程知识点，也可以追加当前项目中真实存在的实现细节，但不能引入无关技术主题。
13. `learning_guide.knowledge_lessons` 可以讲解理解真实项目所必需的工程概念、错误处理和交互逻辑，不要求标题与课程知识点完全一致，但必须引用真实代码并使用通俗语言。
14. 学习章节要说明“解决什么问题、为什么需要、代码怎样完成、看哪里、学完记住什么”，并提供可以亲手验证的小练习。
15. 专业架构、代码证据、测试记录和面试表述继续写入原有专业字段，供面试展示页使用，不要用它们代替 `learning_guide`。
16. `interview_showcase` 专门面向 HR 和技术面试官：只写真实代码或测试能够证明的功能、亮点和难点；每项都要引用真实文件，不能把计划目标当成已完成成果。
17. `implementation_status.task_results` 必须覆盖 `IMPLEMENTATION_PLAN.md` 中的每一项计划任务，`task_title` 原样填写；状态只能是 `verified`、`partial` 或 `not_verified`。只有真实代码和验证记录能够证明的任务才可标为 `verified`。
18. 生成后使用标准 JSON 解析器校验文件，再向用户报告保存位置、已执行测试和未验证内容。

知识库不会接收源码 ZIP。真实性检查由能够读取当前完整工作区的 Codex 完成；知识库会验证回传结构、项目归属、课程知识范围以及路径引用的一致性。
"""


def analysis_result_schema(project_id: int) -> dict:
    """返回 Codex 最终分析结果的 JSON Schema。"""
    string_array = {"type": "array", "items": {"type": "string"}}

    def record_array(properties: dict, required: list[str]) -> dict:
        return {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": required,
                "properties": properties,
            },
        }

    def object_schema(properties: dict) -> dict:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": list(properties),
            "properties": properties,
        }

    project_overview = object_schema({
        "one_sentence": {"type": "string"},
        "problem_story": {"type": "string"},
        "final_result": {"type": "string"},
        "learner_goal": {"type": "string"},
    })
    learning_summary = object_schema({
        "must_remember": string_array,
        "can_ignore_for_now": string_array,
        "teach_back_prompt": {"type": "string"},
        "self_check_questions": string_array,
    })
    learning_guide = object_schema({
        "project_overview": project_overview,
        "prerequisites": record_array({
            "term": {"type": "string"},
            "plain_explanation": {"type": "string"},
            "analogy": {"type": "string"},
            "project_example": {"type": "string"},
            "can_ignore_for_now": {"type": "string"},
        }, ["term", "plain_explanation", "analogy", "project_example", "can_ignore_for_now"]),
        "running_story": record_array({
            "step": {"type": "string"},
            "user_action": {"type": "string"},
            "system_action": {"type": "string"},
            "plain_explanation": {"type": "string"},
            "code_locations": string_array,
        }, ["step", "user_action", "system_action", "plain_explanation", "code_locations"]),
        "chapters": record_array({
            "title": {"type": "string"},
            "learning_goal": {"type": "string"},
            "plain_explanation": {"type": "string"},
            "why_it_matters": {"type": "string"},
            "analogy": {"type": "string"},
            "code_locations": string_array,
            "focus_points": string_array,
            "takeaway": {"type": "string"},
        }, ["title", "learning_goal", "plain_explanation", "why_it_matters", "analogy", "code_locations", "focus_points", "takeaway"]),
        "knowledge_lessons": record_array({
            "knowledge_point": {"type": "string"},
            "what_it_is": {"type": "string"},
            "why_needed": {"type": "string"},
            "without_it": {"type": "string"},
            "project_usage": {"type": "string"},
            "code_locations": string_array,
            "try_it_yourself": {"type": "string"},
        }, ["knowledge_point", "what_it_is", "why_needed", "without_it", "project_usage", "code_locations", "try_it_yourself"]),
        "hands_on": record_array({
            "title": {"type": "string"},
            "action": {"type": "string"},
            "command": {"type": "string"},
            "expected_result": {"type": "string"},
            "what_it_proves": {"type": "string"},
        }, ["title", "action", "command", "expected_result", "what_it_proves"]),
        "common_misunderstandings": record_array({
            "question": {"type": "string"},
            "plain_answer": {"type": "string"},
        }, ["question", "plain_answer"]),
        "exercises": record_array({
            "title": {"type": "string"},
            "task": {"type": "string"},
            "hint": {"type": "string"},
            "expected_learning": {"type": "string"},
        }, ["title", "task", "hint", "expected_learning"]),
        "summary": learning_summary,
    })
    interview_showcase = object_schema({
        "headline": {"type": "string"},
        "verified_features": record_array({
            "name": {"type": "string"},
            "proof": {"type": "string"},
            "evidence_files": string_array,
        }, ["name", "proof", "evidence_files"]),
        "highlights": record_array({
            "title": {"type": "string"},
            "value": {"type": "string"},
            "evidence_files": string_array,
        }, ["title", "value", "evidence_files"]),
        "technical_challenges": record_array({
            "challenge": {"type": "string"},
            "solution": {"type": "string"},
            "evidence_files": string_array,
        }, ["challenge", "solution", "evidence_files"]),
        "pitch_30s": {"type": "string"},
        "pitch_2min": {"type": "string"},
    })
    implementation_status = object_schema({
        "summary": {"type": "string"},
        "task_results": record_array({
            "task_title": {"type": "string"},
            "status": {
                "type": "string",
                "enum": ["verified", "partial", "not_verified"],
            },
            "explanation": {"type": "string"},
            "evidence_files": string_array,
        }, ["task_title", "status", "explanation", "evidence_files"]),
    })

    properties = {
        "project_id": {"type": "integer", "const": project_id},
        "workspace_name": {"type": "string", "minLength": 1},
        "source_fingerprint": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "file_count": {"type": "integer", "minimum": 1},
        "source_size": {"type": "integer", "minimum": 0},
        "file_tree": string_array,
        "language_stats": {
            "type": "object",
            "additionalProperties": {"type": "integer", "minimum": 0},
        },
        "key_files": string_array,
        "implementation_summary": {"type": "string", "minLength": 1},
        "actual_architecture": {"type": "string", "minLength": 1},
        "key_modules": record_array({
            "path": {"type": "string"},
            "responsibility": {"type": "string"},
            "evidence": {"type": "string"},
        }, ["path", "responsibility", "evidence"]),
        "execution_flow": string_array,
        "knowledge_mapping": record_array({
            "knowledge_point": {"type": "string"},
            "code_locations": string_array,
            "explanation": {"type": "string"},
        }, ["knowledge_point", "code_locations", "explanation"]),
        "plan_differences": record_array({
            "planned": {"type": "string"},
            "actual": {"type": "string"},
            "impact": {"type": "string"},
        }, ["planned", "actual", "impact"]),
        "run_and_test": {"type": "string", "minLength": 1},
        "verification_evidence": record_array({
            "command": {"type": "string"},
            "status": {"type": "string", "enum": ["passed", "failed", "not_run"]},
            "summary": {"type": "string"},
            "evidence_files": string_array,
        }, ["command", "status", "summary", "evidence_files"]),
        "interview_demo": string_array,
        "interview_questions": record_array({
            "question": {"type": "string"},
            "answer_points": string_array,
        }, ["question", "answer_points"]),
        "risks_and_limitations": string_array,
        "learning_guide": learning_guide,
        "interview_showcase": interview_showcase,
        "implementation_status": implementation_status,
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Portfolio Codex Analysis Result",
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }
