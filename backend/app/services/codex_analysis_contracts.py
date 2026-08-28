"""Codex 真实代码分析任务说明与 JSON Schema 契约。"""


def analysis_request(project_id: int, task_titles: list[str] | None = None) -> str:
    """生成随项目执行包交付的最终分析说明。"""
    task_section = ""
    if task_titles:
        task_section = "\n\n## implementation_status 标准任务名称\n\n" + "\n".join(
            f"- `{title}`" for title in task_titles
        )
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
10. `learning_guide.beginner_story` 先用一篇连续的大白话故事讲清“项目有什么用、用户做了什么、程序怎样处理、最后得到什么”，不要假设读者学过编程、数学或当前技术。
11. `concept_ladder` 必须按实际使用顺序介绍零基础读者需要的概念。每项先在 `before_term` 中只用日常语言讲明白，再给出专业名称；不得在解释 MNIST、NumPy、卷积、Softmax 等词时依赖另一个尚未解释的专业词。
12. `learning_flow` 用 3-10 步展示用户看到什么、程序做什么以及为什么需要这一步，先建立完整直觉，再进入技术细节。
13. `story_sections` 必须把教学拆成至少 3 个连续章节，每章只增加少量新概念，说明与真实代码的联系，并提供一句读者能用自己的话回答的检查问题；全部章节正文合计不少于 800 个字符。
14. `self_checks` 必须提供至少 3 个零基础自测问题，并给出提示、答案和为什么需要理解，不能只考术语背诵。
15. `learning_guide.code_map` 必须给出真实入口、整体运行流程和覆盖全部人工源码的推荐阅读顺序。`entry_point` 只能填写 `file_tree` 中一个已批注源码的相对路径（例如 `src/main.py`），不得添加函数名、解释文字或多个路径。
16. `learning_guide.source_inventory` 必须逐项覆盖 `file_tree`。人工编写的源码和测试标为 `annotated_source`；安全的辅助文档标为 `supporting_file`；二进制、数据、模型、缓存、生成产物和敏感文件标为 `excluded` 并说明原因。
17. `learning_guide.annotated_files` 必须包含每个 `annotated_source` 的完整 UTF-8 原文、SHA-256 和按行号分段的通俗批注。批注必须从第 1 行连续覆盖到最后一行，不得重叠或遗漏；每段说明作用、必要性、输入输出、前后关系、课程联系和初学者容易看错的地方。
18. 不得将 `.env`、密钥、令牌、密码、私钥或凭据内容写入 JSON。单个源码文本不得超过 200000 字符，全部源码文本合计不得超过 2000000 字符；超限文件必须在 inventory 中标记 `excluded` 并说明。
19. `knowledge_mapping[].knowledge_point` 必须以 `COURSE_KNOWLEDGE.md` 的原始标题为基础。专业架构、代码证据、测试记录和面试表述继续写入原有专业字段，供面试展示页使用，不要用它们代替 `learning_guide`。
20. `implementation_status.task_results` 必须覆盖 `IMPLEMENTATION_PLAN.md` 的“JSON 回传任务名称”清单，`task_title` 必须逐字使用清单中的原始名称，不得添加“阶段 1”等前缀；不要把代码审查、项目讲解、最终验收或 JSON 回传写入 `task_results`。状态只能是 `verified`、`partial` 或 `not_verified`。只有真实代码和验证记录能够证明的任务才可标为 `verified`。
21. 生成后使用标准 JSON 解析器校验文件，再向用户报告保存位置、已执行测试和未验证内容。
{task_section}

知识库不会接收源码 ZIP。真实性检查由能够读取当前完整工作区的 Codex 完成；知识库会验证回传结构、项目归属、课程知识范围以及路径引用的一致性。
"""


def analysis_result_schema(
    project_id: int,
    task_titles: list[str] | None = None,
) -> dict:
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

    beginner_story = object_schema({
        "title": {"type": "string"},
        "content": {"type": "string"},
        "after_reading": {"type": "string"},
        "quick_verification": object_schema({
            "action": {"type": "string"},
            "command": {"type": "string"},
            "expected_result": {"type": "string"},
            "what_it_proves": {"type": "string"},
        }),
    })
    concept_ladder = record_array({
        "term": {"type": "string"},
        "before_term": {"type": "string"},
        "plain_explanation": {"type": "string"},
        "analogy": {"type": "string"},
        "project_role": {"type": "string"},
        "remember": {"type": "string"},
    }, [
        "term", "before_term", "plain_explanation", "analogy",
        "project_role", "remember",
    ])
    learning_flow = record_array({
        "label": {"type": "string"},
        "what_user_sees": {"type": "string"},
        "what_program_does": {"type": "string"},
        "why_needed": {"type": "string"},
        "technical_terms": string_array,
    }, [
        "label", "what_user_sees", "what_program_does", "why_needed",
        "technical_terms",
    ])
    story_sections = record_array({
        "title": {"type": "string"},
        "learning_goal": {"type": "string"},
        "content": {"type": "string"},
        "new_terms": string_array,
        "code_locations": string_array,
        "checkpoint": {"type": "string"},
    }, [
        "title", "learning_goal", "content", "new_terms", "code_locations",
        "checkpoint",
    ])
    self_checks = record_array({
        "question": {"type": "string"},
        "hint": {"type": "string"},
        "answer": {"type": "string"},
        "why_it_matters": {"type": "string"},
    }, ["question", "hint", "answer", "why_it_matters"])
    code_map = object_schema({
        "overview": {"type": "string"},
        "entry_point": {
            "type": "string",
            "description": "仅填写一个已批注源码的 file_tree 相对路径，例如 src/main.py；不要添加解释文字、函数名或其他入口。",
        },
        "runtime_flow": string_array,
        "reading_order": record_array({
            "path": {"type": "string"},
            "role": {"type": "string"},
            "why_read_now": {"type": "string"},
        }, ["path", "role", "why_read_now"]),
    })
    source_inventory = record_array({
        "path": {"type": "string"},
        "category": {
            "type": "string",
            "enum": ["annotated_source", "supporting_file", "excluded"],
        },
        "reason": {"type": "string"},
    }, ["path", "category", "reason"])
    annotation = record_array({
        "start_line": {"type": "integer", "minimum": 1},
        "end_line": {"type": "integer", "minimum": 1},
        "title": {"type": "string"},
        "plain_explanation": {"type": "string"},
        "why_needed": {"type": "string"},
        "input_output": {"type": "string"},
        "connection": {"type": "string"},
        "course_knowledge": {"type": "string"},
        "beginner_warning": {"type": "string"},
    }, [
        "start_line", "end_line", "title", "plain_explanation",
        "why_needed", "input_output", "connection", "course_knowledge",
        "beginner_warning",
    ])
    annotated_files = record_array({
        "path": {"type": "string"},
        "role": {"type": "string"},
        "language": {"type": "string"},
        "source_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "source": {"type": "string"},
        "annotations": annotation,
    }, ["path", "role", "language", "source_sha256", "source", "annotations"])
    learning_guide = object_schema({
        "beginner_story": beginner_story,
        "concept_ladder": concept_ladder,
        "learning_flow": learning_flow,
        "story_sections": story_sections,
        "self_checks": self_checks,
        "code_map": code_map,
        "source_inventory": source_inventory,
        "annotated_files": annotated_files,
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
            "task_title": {
                "type": "string",
                **({"enum": task_titles} if task_titles else {}),
            },
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
