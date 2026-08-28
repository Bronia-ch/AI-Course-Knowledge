"""收尾阶段的关键数据安全回归测试。"""

import asyncio
import hashlib
import io
import json
import tempfile
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.ai.deepseek_client import DeepSeekClient
from app.ai.prompts import build_portfolio_concept_guide_prompt
from app.database import Base, engine
from app.models.models import (
    Chapter,
    Course,
    KnowledgePoint,
    KnowledgeProjectRelation,
    Lesson,
    PortfolioExecutionPackage,
    PortfolioOpportunity,
    PortfolioProject,
    Project,
    Transcript,
)
from app.routers.project_relations import get_project_knowledge_points
from app.schemas.course import ChapterDetail, CourseDetail
from app.schemas.progress import LessonProgressCreate
from app.services.codex_analysis_contracts import (
    analysis_request,
    analysis_result_schema,
)
from app.services.codex_analysis_service import (
    _derive_interview_showcase,
    analysis_request as service_analysis_request,
    analysis_result_schema as service_analysis_result_schema,
)
from app.services.codex_analysis_normalizers import (
    knowledge_reference_allowed,
    location_exists,
    normalize_learning_guide,
    normalize_implementation_status,
    paths,
    validate_result_references,
)
from app.services.execution_export_service import _implementation_plan
from app.services.upload_service import save_audio_file
from app.services.analysis_service import run_analysis
from app.services.transcription_service import run_transcription
from app.services.transcription_quality import (
    TranscriptionQualityError,
    validate_transcription,
)
from app.services.course_service import get_course_tree
from app.services.portfolio_formatters import (
    build_codex_final_return_prompt,
    build_execution_package_markdown,
    build_portfolio_overview_markdown,
)
from app.services.portfolio_data_utils import (
    normalize_optional_url,
    parse_json_dict,
    parse_record_list,
    parse_string_list,
    record_list,
    strip_code_fence,
)
from app.services.portfolio_normalizers import (
    normalize_execution_package,
    normalize_opportunities,
    normalize_project_blueprint,
)
from app.services.portfolio_learning_service import (
    _metric_excerpt,
    concept_guide_to_dict,
    import_codex_concept_guide,
    normalize_concept_guide,
    normalize_reference_sources,
)
from app.services.portfolio_service import (
    import_codex_portfolio_project,
    increment_portfolio_learning_count,
)
from app.services.portfolio_serializers import (
    opportunity_to_dict,
    portfolio_execution_package_to_dict,
    portfolio_project_to_dict,
    project_implementation_status,
)
from app.time_utils import utc_now


class DeepSeekJsonResponseTests(unittest.TestCase):
    @staticmethod
    def _response(content, finish_reason="stop"):
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )],
            usage=SimpleNamespace(total_tokens=10),
        )

    def _client(self, responses):
        client = DeepSeekClient.__new__(DeepSeekClient)
        client.model = "test-model"
        client._create_completion = MagicMock(side_effect=responses)
        return client

    def test_json_mode_retries_empty_response_then_succeeds(self):
        client = self._client([
            self._response(""),
            self._response('{"status": "ok"}'),
        ])

        result = client.chat_json("system json", "user")

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(client._create_completion.call_count, 2)
        self.assertTrue(
            client._create_completion.call_args_list[0].kwargs["json_mode"]
        )

    def test_json_mode_reports_readable_error_after_two_failures(self):
        client = self._client([
            self._response("not json"),
            self._response("{", finish_reason="length"),
        ])

        with self.assertRaisesRegex(ValueError, "连续两次.*length"):
            client.chat_json("system json", "user")

    def test_json_mode_uses_compact_retry_instruction_after_length_cutoff(self):
        client = self._client([
            self._response("{", finish_reason="length"),
            self._response('{"status": "ok"}'),
        ])

        result = client.chat_json(
            "system json",
            "user",
            retry_instruction="只保留核心字段并返回完整 JSON。",
        )

        self.assertEqual(result, {"status": "ok"})
        retry_message = client._create_completion.call_args_list[1].kwargs[
            "user_message"
        ]
        self.assertIn("只保留核心字段", retry_message)

    def test_json_parser_keeps_markdown_compatibility(self):
        result = DeepSeekClient._parse_json_content(
            '```json\n{"status": "ok"}\n```'
        )
        self.assertEqual(result, {"status": "ok"})

    def test_json_parser_does_not_extract_nested_directory_code_block(self):
        content = json.dumps({
            "directory_structure": "```text\nproject_root/\n└── src/\n```",
            "status": "ok",
        }, ensure_ascii=False)

        result = DeepSeekClient._parse_json_content(content)

        self.assertEqual(result["status"], "ok")
        self.assertIn("project_root/", result["directory_structure"])

    def test_concept_guide_is_generated_in_four_bounded_parts(self):
        client = DeepSeekClient.__new__(DeepSeekClient)
        client.chat_json = MagicMock(side_effect=[
            {"guide_title": "指南", "beginner_story": {}},
            {"learning_flow": []},
            {"concept_ladder": []},
            {"story_sections": [], "self_checks": []},
        ])

        result = client.create_portfolio_concept_guide({}, "转写", [], [])

        self.assertEqual(client.chat_json.call_count, 4)
        self.assertEqual(result["guide_title"], "指南")
        self.assertIn("story_sections", result)
        self.assertLessEqual(
            client.chat_json.call_args_list[0].kwargs["max_tokens"], 2500
        )
        self.assertLessEqual(
            client.chat_json.call_args_list[1].kwargs["max_tokens"], 4000
        )
        self.assertLessEqual(
            client.chat_json.call_args_list[2].kwargs["max_tokens"], 6000
        )
        self.assertLessEqual(
            client.chat_json.call_args_list[3].kwargs["max_tokens"], 4000
        )


class PortfolioConceptGuideTests(unittest.TestCase):
    @staticmethod
    def _guide(source_url="https://github.com/example/flowers"):
        concept = {
            "term": "Epoch",
            "before_term": "把全部练习题做完一次",
            "plain_explanation": "完整看过训练集一次",
            "analogy": "做完一遍练习册",
            "project_role": "观察每轮训练变化",
            "remember": "一轮不是一个批次",
        }
        flow = {
            "label": "训练",
            "what_user_sees": "准确率",
            "what_program_would_do": "根据错误更新参数",
            "why_needed": "让模型逐步学习",
            "technical_terms": ["Epoch"],
        }
        section = {
            "title": "理解训练变化",
            "learning_goal": "看懂准确率",
            "content": "这是用于验证连续教学长度的通俗讲解。" * 30,
            "new_terms": ["准确率"],
            "checkpoint": "准确率表示什么？",
        }
        return {
            "guide_title": "从零理解花朵分类",
            "beginner_story": {
                "title": "训练一位识花学生",
                "content": "\n".join([
                    "先拿一张花朵图片作为贯穿示例，观察它的颜色和花瓣位置。" * 8,
                    "程序先把图片整理成保留位置的数字格子，再逐步寻找局部线索。" * 8,
                    "接着把局部线索组合成候选花名，并和正确标签进行比较。" * 8,
                    "最后使用没有参与练习的新图片检查是否真的学会，而不是只记住训练题。" * 8,
                ]),
                "after_reading": "能说清项目输入和输出。",
            },
            "concept_ladder": [{
                **concept,
                "before_term": f"第 {index + 1} 个生活问题",
                "analogy": f"第 {index + 1} 个不同的生活类比",
                "project_role": f"当输入第 {index + 1} 张示例图片时，这一步负责完成对应处理",
            } for index in range(8)],
            "learning_flow": [flow.copy() for _ in range(4)],
            "story_sections": [section.copy() for _ in range(5)],
            "reference_results": [{
                "claim": "公开项目报告准确率 80%",
                "source_name": "example/flowers",
                "source_url": source_url,
                "source_context": "相似数据集和模型",
                "differences": "训练配置可能不同",
                "disclaimer": "这是外部参考结果，不是当前作品实际运行结果",
            }],
            "self_checks": [{
                "question": "为什么需要验证集？",
                "hint": "模拟考试",
                "answer": "用于选择模型",
                "why_it_matters": "避免把测试集用于选模",
            } for _ in range(3)],
            "expected_outcomes": ["理解完整流程"],
            "limitations": ["尚未真实开发"],
            "source_learning": {
                "title": "想继续学习源码？",
                "description": "这是可选步骤",
                "develop_option": "让 Codex 开发",
                "reference_option": "学习相似开源项目",
            },
        }

    def test_metric_excerpt_keeps_only_numbered_metric_lines(self):
        excerpt = _metric_excerpt(
            "Install dependencies\nEpoch 1 accuracy: 72.5%\nAccuracy has improved\nloss=0.42\n"
            "Target accuracy: 99%\n"
            "![Apache License 2.0](https://img.shields.io/badge/license-Apache%202.0.svg)\n"
            "Put dataset under data_path/flowers102"
        )
        self.assertIn("72.5%", excerpt)
        self.assertIn("loss=0.42", excerpt)
        self.assertNotIn("Install dependencies", excerpt)
        self.assertNotIn("Accuracy has improved", excerpt)
        self.assertNotIn("Target accuracy: 99%", excerpt)
        self.assertNotIn("License 2.0", excerpt)
        self.assertNotIn("flowers102", excerpt)

    def test_metric_excerpt_requires_query_context(self):
        readme = (
            "Flowers102 experiment\nAccuracy: 91.25%\n"
            + "\n".join(f"setup note {index}" for index in range(13))
            + "\nUnrelated CIFAR notes\nAccuracy: 80.00%\n"
        )
        excerpt = _metric_excerpt(readme, "Flowers102 accuracy")
        self.assertIn("Flowers102 experiment", excerpt)
        self.assertIn("91.25%", excerpt)
        self.assertNotIn("80.00%", excerpt)

    def test_concept_guide_prompt_bounds_large_context(self):
        sources = [
            {
                "source_name": f"source-{index}",
                "source_url": f"https://github.com/example/{index}",
                "metric_excerpt": "M" * 5000,
                "description": "D" * 1000,
            }
            for index in range(5)
        ]
        prompt = build_portfolio_concept_guide_prompt(
            {"title": "测试项目", "detail": "P" * 20000},
            "T" * 50000,
            [{"title": "K" * 15000}],
            sources,
        )

        self.assertLess(len(prompt), 52000)
        self.assertEqual(prompt.count("M" * 2500), 4)
        self.assertNotIn("source-4", prompt)
        self.assertNotIn("T" * 16001, prompt)

    def test_guide_accepts_traceable_external_result(self):
        source = {
            "source_url": "https://github.com/example/flowers",
            "metric_excerpt": "任务上下文: Flowers102\nAccuracy: 80%",
        }
        normalized = normalize_concept_guide(self._guide(), [source])
        self.assertEqual(len(normalized["concept_ladder"]), 8)
        self.assertIn("不是当前作品", normalized["reference_results"][0]["disclaimer"])

    def test_guide_rejects_repeated_concept_analogies(self):
        source = {
            "source_url": "https://github.com/example/flowers",
            "metric_excerpt": "任务上下文: Flowers102\nAccuracy: 80%",
        }
        data = self._guide()
        for item in data["concept_ladder"]:
            item["analogy"] = "重复的生活类比"

        with self.assertRaisesRegex(ValueError, "analogy 重复过多"):
            normalize_concept_guide(data, [source])

    def test_guide_accepts_trailing_source_slash(self):
        source = {
            "source_url": "https://github.com/example/flowers",
            "metric_excerpt": "任务上下文: Flowers102\nAccuracy: 80%",
        }
        normalized = normalize_concept_guide(
            self._guide("https://github.com/example/flowers/"),
            [source],
        )
        self.assertEqual(
            normalized["reference_results"][0]["source_url"],
            "https://github.com/example/flowers",
        )

    def test_guide_fills_optional_source_learning_copy(self):
        data = self._guide()
        data["source_learning"] = {"title": "想看源码"}
        source = {
            "source_url": "https://github.com/example/flowers",
            "metric_excerpt": "任务上下文: Flowers102\nAccuracy: 80%",
        }

        normalized = normalize_concept_guide(data, [source])

        self.assertEqual(normalized["source_learning"]["title"], "想看源码")
        self.assertIn("Codex", normalized["source_learning"]["develop_option"])

    def test_guide_rejects_unsearched_external_result(self):
        source = {"source_url": "https://github.com/example/flowers"}
        with self.assertRaisesRegex(ValueError, "未检索到"):
            normalize_concept_guide(
                self._guide("https://github.com/unknown/repository"),
                [source],
            )

    def test_codex_reference_sources_are_bounded_and_deduplicated(self):
        sources = normalize_reference_sources([
            {
                "source_name": "示例来源",
                "source_url": "https://github.com/example/flowers",
                "metric_excerpt": "M" * 10000,
            },
            {
                "source_name": "重复来源",
                "source_url": "https://github.com/example/flowers/",
            },
        ])
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(sources[0]["metric_excerpt"]), 9000)
        self.assertIn("Codex", sources[0]["usage_notice"])

    def test_guide_rejects_number_missing_from_source_excerpt(self):
        source = {
            "source_url": "https://github.com/example/flowers",
            "metric_excerpt": "任务上下文: Flowers102\nAccuracy: 75%",
        }
        with self.assertRaisesRegex(ValueError, "不存在的数字"):
            normalize_concept_guide(self._guide(), [source])


class CodexPortfolioImportTests(unittest.TestCase):
    def setUp(self):
        self.local_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.local_engine)
        self.session_factory = sessionmaker(bind=self.local_engine)
        db = self.session_factory()
        course = Course(title="Codex 导入测试课程")
        db.add(course)
        db.flush()
        chapter = Chapter(course_id=course.id, title="测试章节", order_index=1)
        db.add(chapter)
        db.flush()
        lesson = Lesson(chapter_id=chapter.id, title="测试课节", status="completed")
        db.add(lesson)
        db.flush()
        db.add(Transcript(
            lesson_id=lesson.id,
            start_time=0,
            end_time=5,
            text="课程讲解允许知识点",
        ))
        db.add(KnowledgePoint(
            lesson_id=lesson.id,
            title="允许知识点",
            description="课程中的真实知识",
        ))
        opportunity = PortfolioOpportunity(
            lesson_id=lesson.id,
            chapter_id=chapter.id,
            title="Codex 作品",
            project_type="topic_project",
            ability_claim="能够完成作品分析",
            description="作品候选说明",
            knowledge_points='["允许知识点"]',
            core_features='["核心功能"]',
            interview_value="可以用于面试说明",
            estimated_effort="两天",
            recommended=True,
        )
        db.add(opportunity)
        db.commit()
        self.opportunity_id = opportunity.id
        db.close()

    def tearDown(self):
        self.local_engine.dispose()

    def test_codex_blueprint_and_guide_import_do_not_call_deepseek(self):
        db = self.session_factory()
        try:
            blueprint = {
                "title": "Codex 作品",
                "objective": "让初学者理解完整流程",
                "use_case": "课程学习与面试展示",
                "architecture": "输入、处理、输出三层结构",
                "technology_stack": ["Python"],
                "core_features": ["核心功能"],
                "knowledge_points": ["允许知识点", "越界知识点"],
                "deliverables": ["学习报告"],
                "acceptance_criteria": ["能够讲清流程"],
                "interview_pitch": "我完成了完整分析",
                "estimated_effort": "两天",
                "tasks": [{
                    "title": "理解流程",
                    "description": "按顺序学习",
                    "acceptance_criteria": "可以复述",
                }],
            }
            with patch("app.services.portfolio_service.DeepSeekClient") as model:
                project = import_codex_portfolio_project(
                    db, self.opportunity_id, blueprint
                )
            model.assert_not_called()
            self.assertEqual(project.knowledge_points, '["允许知识点"]')
            self.assertEqual(len(project.tasks), 1)

            source_url = "https://github.com/example/flowers"
            guide_payload = {
                "content": PortfolioConceptGuideTests._guide(source_url),
                "reference_sources": [{
                    "source_name": "example/flowers",
                    "source_url": source_url,
                    "metric_excerpt": "任务上下文: Flowers102\nAccuracy: 80%",
                }],
                "reference_status": "found",
            }
            with patch("app.services.portfolio_learning_service.DeepSeekClient") as model:
                guide = import_codex_concept_guide(db, project.id, guide_payload)
            model.assert_not_called()
            saved = concept_guide_to_dict(guide)
            self.assertEqual(saved["reference_status"], "found")
            self.assertEqual(len(saved["content"]["concept_ladder"]), 8)
        finally:
            db.close()

    def test_learning_completion_count_increments_and_serializes(self):
        db = self.session_factory()
        try:
            blueprint = {
                "title": "Codex 作品",
                "objective": "让初学者理解完整流程",
                "use_case": "课程学习",
                "architecture": "输入、处理、输出三层结构",
                "technology_stack": ["Python"],
                "core_features": ["核心功能"],
                "knowledge_points": ["允许知识点"],
                "deliverables": ["学习报告"],
                "acceptance_criteria": ["能够讲清流程"],
                "interview_pitch": "我完成了完整分析",
                "estimated_effort": "两天",
                "tasks": [{
                    "title": "理解流程",
                    "description": "按顺序学习",
                    "acceptance_criteria": "可以复述",
                }],
            }
            project = import_codex_portfolio_project(
                db,
                self.opportunity_id,
                blueprint,
            )
            self.assertEqual(project.learning_count, 0)

            first = increment_portfolio_learning_count(db, project.id)
            self.assertEqual(first.learning_count, 1)
            second = increment_portfolio_learning_count(db, project.id)
            self.assertEqual(second.learning_count, 2)
            self.assertEqual(
                portfolio_project_to_dict(second)["learning_count"],
                2,
            )

            opportunity = db.query(PortfolioOpportunity).filter(
                PortfolioOpportunity.id == self.opportunity_id
            ).one()
            self.assertEqual(opportunity_to_dict(opportunity)["learning_count"], 2)
            self.assertIsNone(increment_portfolio_learning_count(db, 999999))
        finally:
            db.close()


class CodexAnalysisContractTests(unittest.TestCase):
    def test_contract_keeps_required_learning_and_interview_sections(self):
        schema = analysis_result_schema(42)
        properties = schema["properties"]
        self.assertEqual(properties["project_id"]["const"], 42)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(properties))
        self.assertIn("learning_guide", schema["required"])
        self.assertIn("interview_showcase", schema["required"])
        self.assertIn("implementation_status", schema["required"])
        guide_schema = properties["learning_guide"]
        self.assertEqual(
            set(guide_schema["required"]),
            {
                "beginner_story", "concept_ladder", "learning_flow",
                "story_sections", "self_checks", "code_map",
                "source_inventory", "annotated_files",
            },
        )

        status_enum = properties["implementation_status"]["properties"][
            "task_results"
        ]["items"]["properties"]["status"]["enum"]
        self.assertEqual(status_enum, ["verified", "partial", "not_verified"])
        json.dumps(schema)

    def test_request_and_legacy_import_path_keep_json_handoff(self):
        prompt = analysis_request(42)
        self.assertIn("portfolio_analysis_result.json", prompt)
        self.assertIn("`project_id` 必须填写 `42`", prompt)
        self.assertEqual(service_analysis_request(42), prompt)
        self.assertEqual(
            service_analysis_result_schema(42),
            analysis_result_schema(42),
        )

    def test_implementation_status_accepts_repeated_phase_prefixes(self):
        task = SimpleNamespace(id=7, title="数据加载与预处理")
        result = normalize_implementation_status({
            "summary": "已核对计划",
            "task_results": [{
                "task_title": "阶段 1：阶段1：数据加载与预处理",
                "status": "not_verified",
                "explanation": "未运行数据集下载",
                "evidence_files": [],
            }],
        }, [task])

        self.assertEqual(result["task_results"][0]["task_id"], 7)
        self.assertEqual(
            result["task_results"][0]["task_title"], "数据加载与预处理"
        )

    def test_implementation_status_separates_extra_workflow_steps(self):
        tasks = [
            SimpleNamespace(id=7, title="数据加载与预处理"),
            SimpleNamespace(id=8, title="实现卷积层前向传播"),
        ]
        result = normalize_implementation_status({
            "summary": "已核对开发和收尾流程",
            "task_results": [
                {
                    "task_title": "阶段 1：数据加载与预处理",
                    "status": "not_verified",
                    "explanation": "未下载数据集",
                    "evidence_files": [],
                },
                {
                    "task_title": "阶段 2：实现卷积层前向传播",
                    "status": "verified",
                    "explanation": "代码和测试均存在",
                    "evidence_files": ["src/conv.py"],
                },
                {
                    "task_title": "阶段 8：最终验收与 JSON 回传",
                    "status": "verified",
                    "explanation": "已生成回传文件",
                    "evidence_files": [],
                },
            ],
        }, tasks)

        self.assertEqual(len(result["task_results"]), 2)
        self.assertEqual(len(result["workflow_results"]), 1)
        self.assertIsNone(result["workflow_results"][0]["task_id"])

    def test_implementation_status_still_rejects_missing_project_tasks(self):
        task = SimpleNamespace(id=7, title="数据加载与预处理")
        with self.assertRaisesRegex(ValueError, "未覆盖全部计划任务"):
            normalize_implementation_status({
                "summary": "只有收尾流程",
                "task_results": [{
                    "task_title": "阶段 8：最终验收与 JSON 回传",
                    "status": "verified",
                    "explanation": "已生成回传文件",
                    "evidence_files": [],
                }],
            }, [task])

    def test_project_schema_and_request_constrain_exact_task_titles(self):
        titles = ["数据加载与预处理", "实现卷积层前向传播"]
        schema = analysis_result_schema(42, titles)
        task_title = schema["properties"]["implementation_status"][
            "properties"
        ]["task_results"]["items"]["properties"]["task_title"]
        prompt = analysis_request(42, titles)

        self.assertEqual(task_title["enum"], titles)
        self.assertIn("- `数据加载与预处理`", prompt)
        self.assertIn("不要把代码审查", prompt)

    @staticmethod
    def _annotated_guide(source="print('hello')\n"):
        return {
            "beginner_story": {
                "title": "从输入到输出",
                "content": "这是一段面向零基础用户的连续项目故事。" * 30,
                "after_reading": "能用自己的话说明整个运行过程。",
                "quick_verification": {
                    "action": "运行程序",
                    "command": "python main.py",
                    "expected_result": "看到 hello",
                    "what_it_proves": "入口可以正常执行",
                },
            },
            "code_map": {
                "overview": "main.py 是完整程序入口。",
                "entry_point": "main.py",
                "runtime_flow": ["读取入口", "打印结果"],
                "reading_order": [{
                    "path": "main.py",
                    "role": "程序入口",
                    "why_read_now": "先看懂最小执行流程",
                }],
            },
            "source_inventory": [
                {"path": "main.py", "category": "annotated_source", "reason": "人工源码"},
                {"path": "README.md", "category": "supporting_file", "reason": "说明文档"},
                {"path": "model.bin", "category": "excluded", "reason": "二进制模型"},
            ],
            "annotated_files": [{
                "path": "main.py",
                "role": "程序入口",
                "language": "Python",
                "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                "source": source,
                "annotations": [{
                    "start_line": 1,
                    "end_line": len(source.splitlines()),
                    "title": "输出结果",
                    "plain_explanation": "让 Python 把一句话显示在屏幕上。",
                    "why_needed": "用来证明程序已经运行。",
                    "input_output": "没有外部输入，输出 hello。",
                    "connection": "这是入口的全部流程。",
                    "course_knowledge": "对应 Python 程序执行。",
                    "beginner_warning": "字符串必须放在引号中。",
                }],
            }],
        }

    def test_annotated_guide_keeps_full_source_and_line_notes(self):
        file_tree = ["main.py", "README.md", "model.bin"]
        guide = normalize_learning_guide(self._annotated_guide(), file_tree)

        self.assertEqual(guide["code_map"]["entry_point"], "main.py")
        self.assertEqual(guide["annotated_files"][0]["source"], "print('hello')\n")
        self.assertEqual(guide["annotated_files"][0]["annotations"][0]["end_line"], 1)
        self.assertEqual(guide["concept_ladder"], [])

    def test_annotated_guide_keeps_progressive_beginner_teaching_path(self):
        guide = self._annotated_guide()
        guide["concept_ladder"] = [{
            "term": f"概念 {index}",
            "before_term": "先用日常语言说明它解决的事情。",
            "plain_explanation": "理解事情以后，再认识这个专业名称。",
            "analogy": "像按答案练习的练习册。",
            "project_role": "帮助程序完成当前处理步骤。",
            "remember": "先理解用途，不背定义。",
        } for index in range(3)]
        guide["learning_flow"] = [{
            "label": f"步骤 {index}",
            "what_user_sees": "看到输入逐渐变成结果。",
            "what_program_does": "完成当前这一小步处理。",
            "why_needed": "为下一步准备可以使用的信息。",
            "technical_terms": [f"概念 {index}"],
        } for index in range(3)]
        guide["story_sections"] = [{
            "title": f"只学一件事 {index}",
            "learning_goal": "能用自己的话说明这一小步。",
            "content": "这段内容先从生活中的例子讲起，再联系到项目实际发生的事情。" * 16,
            "new_terms": [f"概念 {index}"],
            "code_locations": ["main.py"],
            "checkpoint": "这一小步的输入和输出分别是什么？",
        } for index in range(3)]
        guide["self_checks"] = [{
            "question": f"问题 {index}",
            "hint": "回想刚才看到的生活例子。",
            "answer": "用自己的话说明用途即可。",
            "why_it_matters": "证明理解了作用而不是背术语。",
        } for index in range(3)]

        normalized = normalize_learning_guide(
            guide,
            ["main.py", "README.md", "model.bin"],
        )

        self.assertEqual(len(normalized["concept_ladder"]), 3)
        self.assertEqual(len(normalized["story_sections"]), 3)
        self.assertEqual(normalized["story_sections"][0]["code_locations"], ["main.py"])

    def test_annotated_guide_extracts_entry_path_from_codex_explanation(self):
        guide = self._annotated_guide()
        guide["code_map"]["entry_point"] = (
            "主要训练入口是 main.py 的 main；运行后会输出结果。"
        )

        normalized = normalize_learning_guide(
            guide,
            ["main.py", "README.md", "model.bin"],
        )

        self.assertEqual(normalized["code_map"]["entry_point"], "main.py")

    def test_annotated_guide_rejects_entry_without_real_annotated_path(self):
        guide = self._annotated_guide()
        guide["code_map"]["entry_point"] = "入口由外部工具自动决定。"

        with self.assertRaisesRegex(ValueError, "无法从以下内容识别路径"):
            normalize_learning_guide(
                guide,
                ["main.py", "README.md", "model.bin"],
            )

    def test_annotated_guide_rejects_line_gaps(self):
        source = "first\nsecond\nthird"
        guide = self._annotated_guide(source)
        guide["annotated_files"][0]["annotations"] = [
            {**guide["annotated_files"][0]["annotations"][0], "start_line": 1, "end_line": 1},
            {**guide["annotated_files"][0]["annotations"][0], "start_line": 3, "end_line": 3},
        ]

        with self.assertRaisesRegex(ValueError, "必须连续"):
            normalize_learning_guide(guide, ["main.py", "README.md", "model.bin"])

    def test_annotated_guide_rejects_incomplete_inventory(self):
        guide = self._annotated_guide()
        guide["source_inventory"].pop()

        with self.assertRaisesRegex(ValueError, "未覆盖全部文件"):
            normalize_learning_guide(guide, ["main.py", "README.md", "model.bin"])

    def test_implementation_plan_lists_exact_json_task_titles(self):
        project = SimpleNamespace(tasks=[
            SimpleNamespace(title="数据加载与预处理"),
            SimpleNamespace(title="实现卷积层前向传播"),
        ])
        markdown = _implementation_plan(project, {"implementation_phases": []})

        self.assertIn("JSON 回传任务名称", markdown)
        self.assertIn("- `数据加载与预处理`", markdown)
        self.assertIn("不要添加“阶段 1”等前缀", markdown)


class PortfolioSerializerTests(unittest.TestCase):
    def test_legacy_lesson_opportunity_keeps_source_lesson(self):
        lesson = Lesson(
            id=7,
            chapter_id=1,
            title="旧课节",
            status="completed",
            created_at=utc_now(),
        )
        opportunity = PortfolioOpportunity(
            id=8,
            lesson_id=lesson.id,
            chapter_id=None,
            title="旧版作品",
            project_type="micro_demo",
            ability_claim="能力",
            description="说明",
            knowledge_points='["知识点"]',
            core_features='["功能"]',
            interview_value="价值",
            estimated_effort="一天",
            recommended=True,
            created_at=utc_now(),
        )
        opportunity.lesson = lesson
        result = opportunity_to_dict(opportunity)
        self.assertEqual(result["source_scope"], "lesson")
        self.assertEqual(result["covered_lessons"], [{"id": 7, "title": "旧课节"}])

    def test_pending_project_has_conservative_implementation_status(self):
        project = PortfolioProject(
            id=9,
            opportunity_id=8,
            lesson_id=7,
            chapter_id=None,
            title="待分析项目",
            project_type="topic_project",
            objective="目标",
            use_case="场景",
            architecture="架构",
            technology_stack='["Python"]',
            core_features="[]",
            knowledge_points="[]",
            deliverables="[]",
            acceptance_criteria="[]",
            interview_pitch="讲述",
            estimated_effort="两天",
            status="planning",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        status = project_implementation_status(project)
        result = portfolio_project_to_dict(project)
        self.assertEqual(status["overall_status"], "pending_analysis")
        self.assertEqual(result["status"], "planning")
        self.assertEqual(result["technology_stack"], ["Python"])

    def test_execution_package_adds_missing_codex_handoff(self):
        package = PortfolioExecutionPackage(
            id=10,
            project_id=42,
            project_brief="需求",
            technology_choices="[]",
            architecture="架构",
            directory_structure="src/",
            data_models="[]",
            api_contracts="[]",
            implementation_phases="[]",
            test_plan="[]",
            acceptance_checklist="[]",
            readme_requirements="[]",
            codex_master_prompt="开发提示词",
            review_prompt="审查提示词",
            explanation_prompt="讲解提示词",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        result = portfolio_execution_package_to_dict(package)
        self.assertIn("portfolio_analysis_result.json", result["codex_master_prompt"])
        self.assertEqual(result["implementation_phases"][-1]["title"], "最终验收与 JSON 回传")
        self.assertIn("# AI 项目执行包", result["markdown_content"])


class PortfolioNormalizerTests(unittest.TestCase):
    def test_opportunities_filter_types_and_limit_count(self):
        valid = {
            "title": "候选作品",
            "project_type": "topic_project",
            "knowledge_points": ["知识点"],
        }
        result = normalize_opportunities(
            [valid.copy() for _index in range(7)]
            + [{"title": "无效类型", "project_type": "unknown"}]
        )
        self.assertEqual(len(result), 6)
        self.assertTrue(all(item["project_type"] == "topic_project" for item in result))

    def test_project_blueprint_limits_tasks_and_knowledge_scope(self):
        opportunity = PortfolioOpportunity(
            lesson_id=1,
            title="课程作品",
            project_type="topic_project",
            ability_claim="能力",
            description="说明",
            knowledge_points='["课程知识", "备用知识"]',
            core_features="[]",
            interview_value="面试价值",
            estimated_effort="两天",
        )
        blueprint = normalize_project_blueprint(
            {
                "objective": "完成项目",
                "architecture": "分层架构",
                "knowledge_points": ["课程知识", "越界知识"],
                "tasks": [
                    {"title": f"任务 {index}"}
                    for index in range(10)
                ],
            },
            opportunity,
            {"课程知识", "备用知识"},
        )
        self.assertEqual(json.loads(blueprint["knowledge_points"]), ["课程知识"])
        self.assertEqual(len(blueprint["tasks"]), 8)

    def test_execution_package_requires_text_and_limits_phases(self):
        base = {
            "project_brief": "需求",
            "architecture": "架构",
            "directory_structure": "```text\nsrc/\n```",
            "implementation_phases": [
                {
                    "title": f"阶段 {index}",
                    "objective": f"目标 {index}",
                    "tasks": [f"任务 {index}"],
                    "acceptance_criteria": [f"验收 {index}"],
                }
                for index in range(9)
            ],
        }
        normalized = normalize_execution_package(base)
        self.assertEqual(normalized["directory_structure"], "src/")
        self.assertEqual(len(normalized["implementation_phases"]), 7)
        self.assertIn("项目需求：\n需求", normalized["codex_master_prompt"])
        self.assertIn("任务 0", normalized["implementation_phases"][0]["codex_prompt"])
        self.assertIn("全面审查", normalized["review_prompt"])
        self.assertIn("没有编程基础", normalized["explanation_prompt"])

        with self.assertRaises(ValueError):
            normalize_execution_package({**base, "architecture": ""})

    def test_execution_package_does_not_depend_on_ai_generated_prompts(self):
        normalized = normalize_execution_package({
            "project_brief": "识别手写数字并显示结果。",
            "architecture": "界面调用推理模块，推理模块加载模型。",
            "directory_structure": "src/",
            "codex_master_prompt": "模型生成的冗长提示不应被采用",
            "review_prompt": "模型审查提示",
            "explanation_prompt": "模型讲解提示",
            "implementation_phases": [{
                "title": "完成推理流程",
                "objective": "得到可验证结果",
                "tasks": ["加载模型", "执行预测"],
                "acceptance_criteria": ["测试样例可以得到预测结果"],
                "codex_prompt": "模型阶段提示",
            }],
            "test_plan": ["运行自动化测试"],
            "acceptance_checklist": ["核心流程可用"],
        })

        self.assertNotIn("冗长提示不应被采用", normalized["codex_master_prompt"])
        self.assertNotIn(
            "模型阶段提示",
            normalized["implementation_phases"][0]["codex_prompt"],
        )
        self.assertIn("加载模型", normalized["codex_master_prompt"])


class PortfolioDataUtilsTests(unittest.TestCase):
    def test_invalid_json_returns_safe_empty_values(self):
        self.assertEqual(parse_string_list("not-json"), [])
        self.assertEqual(parse_record_list('{"not": "a list"}'), [])
        self.assertEqual(parse_json_dict("[1, 2]"), {})

    def test_record_cleaning_and_code_fence_removal(self):
        records = record_list(
            [{"name": " Python ", "uses": [" API ", ""]}, "invalid"],
            ("name", "uses"),
            limit=5,
        )
        self.assertEqual(records, [{"name": "Python", "uses": ["API"]}])
        self.assertEqual(strip_code_fence("```text\nsrc/\n```"), "src/")

    def test_optional_url_only_accepts_http_and_https(self):
        self.assertEqual(
            normalize_optional_url(" https://example.com/demo ", "演示地址"),
            "https://example.com/demo",
        )
        self.assertIsNone(normalize_optional_url("", "演示地址"))
        with self.assertRaises(ValueError):
            normalize_optional_url("javascript:alert(1)", "演示地址")


class PortfolioFormatterTests(unittest.TestCase):
    def test_overview_markdown_keeps_interview_sections(self):
        markdown = build_portfolio_overview_markdown({
            "introduction": "作品集简介",
            "capabilities": [],
            "interview_order": [{
                "order": 1,
                "title": "示例项目",
                "headline": "真实实现",
                "objective": "备用目标",
                "resume_bullets": ["完成核心流程"],
            }],
            "technologies": [{"name": "Python", "project_count": 1}],
        })
        self.assertIn("# 个人技术作品集", markdown)
        self.assertIn("### 1. 示例项目", markdown)
        self.assertIn("Python：用于 1 个项目", markdown)

    def test_execution_markdown_and_codex_prompt_keep_required_handoff(self):
        prompt = build_codex_final_return_prompt(42)
        self.assertIn("`project_id` 必须填写 `42`", prompt)
        self.assertIn("portfolio_analysis_result.json", prompt)

        markdown = build_execution_package_markdown({
            "updated_at": utc_now(),
            "project_brief": "项目需求",
            "technology_choices": [],
            "architecture": "系统架构",
            "directory_structure": "src/",
            "data_models": [],
            "api_contracts": [],
            "implementation_phases": [],
            "test_plan": [],
            "acceptance_checklist": [],
            "readme_requirements": [],
            "codex_master_prompt": prompt,
            "review_prompt": "审查提示词",
            "explanation_prompt": "讲解提示词",
        })
        self.assertIn("# AI 项目执行包", markdown)
        self.assertIn("## Codex 完整开发提示词", markdown)
        self.assertIn("portfolio_analysis_result.json", markdown)


class QueryEfficiencyTests(unittest.TestCase):
    def setUp(self):
        self.local_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.local_engine)
        self.session_factory = sessionmaker(bind=self.local_engine)

        db = self.session_factory()
        course = Course(title="查询测试课程")
        db.add(course)
        db.flush()
        for chapter_index in range(2):
            chapter = Chapter(
                course_id=course.id,
                title=f"章节 {chapter_index}",
                order_index=chapter_index,
            )
            db.add(chapter)
            db.flush()
            for lesson_index in range(3):
                lesson = Lesson(chapter_id=chapter.id, title=f"课节 {lesson_index}")
                db.add(lesson)
                db.flush()
                db.add(Transcript(
                    lesson_id=lesson.id,
                    start_time=0,
                    end_time=1,
                    text="测试转录",
                ))
                knowledge_point = KnowledgePoint(
                    lesson_id=lesson.id,
                    title=f"知识点 {chapter_index}-{lesson_index}",
                )
                project = Project(lesson_id=lesson.id, name=f"项目 {lesson_index}")
                db.add_all([knowledge_point, project])
                db.flush()
                db.add(KnowledgeProjectRelation(
                    knowledge_point_id=knowledge_point.id,
                    project_id=project.id,
                    reason="查询测试",
                ))
        db.commit()
        self.course_id = course.id
        self.project_id = project.id
        db.close()

        self.query_count = 0

        def count_query(*_args):
            self.query_count += 1

        self.count_query = count_query
        event.listen(self.local_engine, "before_cursor_execute", self.count_query)

    def tearDown(self):
        event.remove(self.local_engine, "before_cursor_execute", self.count_query)
        self.local_engine.dispose()

    def test_course_tree_query_count_does_not_grow_per_lesson(self):
        db = self.session_factory()
        try:
            course = get_course_tree(db, self.course_id)
            self.assertIsNotNone(course)
            load_query_count = self.query_count
            counts = [
                (lesson.transcript_count, lesson.knowledge_point_count, lesson.project_count)
                for chapter in course.chapters
                for lesson in chapter.lessons
            ]
            self.assertEqual(self.query_count, load_query_count)
            self.assertEqual(counts, [(1, 1, 1)] * 6)
            self.assertLessEqual(load_query_count, 6)
        finally:
            db.close()

    def test_project_knowledge_points_use_two_queries(self):
        db = self.session_factory()
        try:
            result = get_project_knowledge_points(self.project_id, db)
            self.assertEqual(len(result), 1)
            self.assertLessEqual(self.query_count, 2)
        finally:
            db.close()


class TimeCompatibilityTests(unittest.TestCase):
    def test_utc_now_remains_naive_for_existing_sqlite_columns(self):
        value = utc_now()
        self.assertIsNone(value.tzinfo)


class SchemaDefaultTests(unittest.TestCase):
    def test_nested_response_lists_are_not_shared(self):
        first_course = CourseDetail(
            id=1,
            title="课程一",
            description=None,
            created_at=utc_now(),
        )
        second_course = CourseDetail(
            id=2,
            title="课程二",
            description=None,
            created_at=utc_now(),
        )
        first_course.chapters.append("测试章节")
        self.assertEqual(second_course.chapters, [])

        first_chapter = ChapterDetail(
            id=1,
            course_id=1,
            title="章节一",
            order_index=0,
        )
        second_chapter = ChapterDetail(
            id=2,
            course_id=1,
            title="章节二",
            order_index=1,
        )
        first_chapter.lessons.append("测试课节")
        self.assertEqual(second_chapter.lessons, [])


class TranscriptionQualityTests(unittest.TestCase):
    @staticmethod
    def _segments(texts, step=2):
        return [
            {
                "start_time": index * step,
                "end_time": (index + 1) * step,
                "text": text,
            }
            for index, text in enumerate(texts)
        ]

    def test_rejects_dominant_repeated_text(self):
        segments = self._segments(["Thank you."] * 24 + ["课程开始"])
        with self.assertRaises(TranscriptionQualityError):
            validate_transcription(segments)

    def test_rejects_long_consecutive_repetition(self):
        texts = [f"正常内容 {index}" for index in range(30)] + ["Okay."] * 20
        with self.assertRaises(TranscriptionQualityError):
            validate_transcription(self._segments(texts))

    def test_rejects_symbol_only_transcript(self):
        texts = ["։ ։ ։"] * 20 + [f"正常内容 {index}" for index in range(30)]
        with self.assertRaises(TranscriptionQualityError):
            validate_transcription(self._segments(texts))

    def test_accepts_diverse_transcript(self):
        segments = self._segments([f"第 {index} 段课程内容" for index in range(40)])
        validate_transcription(segments)


class WhisperConfigurationTests(unittest.TestCase):
    def test_transcribe_uses_hallucination_resistant_options(self):
        from app.ai.whisper_transcriber import WhisperTranscriber

        model = MagicMock()
        info = SimpleNamespace(language="zh", duration=60)
        model.transcribe.return_value = (iter(()), info)
        transcriber = WhisperTranscriber()
        transcriber._model = model

        segments, returned_info = transcriber.transcribe("sample.wav")

        self.assertIs(returned_info, info)
        self.assertEqual(list(segments), [])
        options = model.transcribe.call_args.kwargs
        self.assertEqual(options["language"], "zh")
        self.assertTrue(options["vad_filter"])
        self.assertFalse(options["condition_on_previous_text"])
        self.assertEqual(options["temperature"], 0.0)
        self.assertEqual(options["no_speech_threshold"], 0.6)


class WhisperLazyLoadingTests(unittest.TestCase):
    def test_model_loads_lazily_and_only_once(self):
        model = object()
        with patch(
            "app.ai.whisper_transcriber.WhisperModel",
            return_value=model,
        ) as model_factory:
            from app.ai.whisper_transcriber import WhisperTranscriber

            transcriber = WhisperTranscriber(device="cpu")
            model_factory.assert_not_called()

            with ThreadPoolExecutor(max_workers=4) as executor:
                loaded_models = list(
                    executor.map(lambda _index: transcriber._ensure_model(), range(8))
                )

            self.assertTrue(all(item is model for item in loaded_models))
            model_factory.assert_called_once()


class DatabaseSafetyTests(unittest.TestCase):
    def test_sqlite_foreign_keys_are_enabled(self):
        with engine.connect() as connection:
            self.assertEqual(connection.execute(text("PRAGMA foreign_keys")).scalar(), 1)
        engine.dispose()


class ProgressValidationTests(unittest.TestCase):
    def test_progress_rejects_out_of_range_values(self):
        with self.assertRaises(ValidationError):
            LessonProgressCreate(progress_percent=101)
        with self.assertRaises(ValidationError):
            LessonProgressCreate(current_time=-1)

    def test_completed_points_default_is_not_shared(self):
        first = LessonProgressCreate()
        second = LessonProgressCreate()
        first.completed_knowledge_points.append(1)
        self.assertEqual(second.completed_knowledge_points, [])


class CodexCompatibilityTests(unittest.TestCase):
    def test_documentation_and_tests_are_not_counted_as_features(self):
        showcase = _derive_interview_showcase(
            "实现说明",
            [
                {"path": "src/main.py", "responsibility": "运行入口", "evidence": "真实代码"},
                {"path": "tests/test_main.py", "responsibility": "测试", "evidence": "测试代码"},
                {"path": "README.md", "responsibility": "文档", "evidence": "说明"},
                {"path": "requirements.txt", "responsibility": "依赖", "evidence": "依赖声明"},
            ],
            [],
            [],
        )
        self.assertEqual(
            [item["evidence_files"] for item in showcase["verified_features"]],
            [["src/main.py"]],
        )

    def test_file_paths_are_normalized_and_unsafe_paths_are_rejected(self):
        self.assertEqual(paths(["./src/main.py", "src/main.py"], 10), ["src/main.py"])
        for unsafe_path in ("../secret.txt", "src/../../secret.txt", "C:/secret.txt"):
            with self.subTest(path=unsafe_path), self.assertRaises(ValueError):
                paths([unsafe_path], 10)

    def test_code_locations_must_reference_an_exact_file(self):
        file_tree = ["src/main.py"]
        self.assertTrue(location_exists("src/main.py:42", file_tree))
        self.assertTrue(location_exists("src/main.py#main", file_tree))
        self.assertFalse(location_exists("src/main.py.bak:42", file_tree))

    def test_combined_knowledge_reference_accepts_covered_course_topics(self):
        allowed = {"SSD目标检测", "dlib追踪器初始化"}
        self.assertTrue(
            knowledge_reference_allowed("SSD目标检测 + dlib追踪器初始化", allowed)
        )
        self.assertTrue(knowledge_reference_allowed("SSD目标检测与结果过滤", allowed))
        self.assertFalse(knowledge_reference_allowed("SSD目标检测与Redis缓存", allowed))

    def test_reference_validation_rejects_missing_module_path(self):
        result = {
            "key_modules": [{"path": "src/missing.py"}],
            "knowledge_mapping": [],
            "verification_evidence": [],
            "interview_showcase": {
                "verified_features": [],
                "highlights": [],
                "technical_challenges": [],
            },
            "implementation_status": {"task_results": []},
            "learning_guide": {
                "running_story": [],
                "chapters": [],
                "knowledge_lessons": [],
            },
        }
        with self.assertRaisesRegex(ValueError, "不存在的路径"):
            validate_result_references(result, ["src/main.py"], set())


class AudioUploadTests(unittest.TestCase):
    @staticmethod
    def _wav_bytes() -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            wav_file.writeframes(b"\x00\x00" * 800)
        return buffer.getvalue()

    def test_audio_is_saved_under_absolute_configured_root(self):
        previous_root = settings.UPLOAD_DIR
        with tempfile.TemporaryDirectory() as temp_dir:
            settings.UPLOAD_DIR = temp_dir
            try:
                upload = UploadFile(
                    filename="sample.wav",
                    file=io.BytesIO(self._wav_bytes()),
                )
                stored_name, relative_dir = asyncio.run(save_audio_file(99, upload))
                saved_path = Path(temp_dir) / relative_dir / stored_name
                self.assertTrue(saved_path.exists())
                self.assertEqual(saved_path.suffix, ".wav")
            finally:
                settings.UPLOAD_DIR = previous_root


class TransactionalReplacementTests(unittest.TestCase):
    def setUp(self):
        self.local_engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.local_engine)
        self.session_factory = sessionmaker(bind=self.local_engine)
        db = self.session_factory()
        course = Course(title="测试课程")
        db.add(course)
        db.flush()
        chapter = Chapter(course_id=course.id, title="测试章节")
        db.add(chapter)
        db.flush()
        lesson = Lesson(chapter_id=chapter.id, title="测试课节", status="analyzing", audio_path="old.wav")
        db.add(lesson)
        db.flush()
        db.add(Transcript(lesson_id=lesson.id, start_time=0, end_time=1, text="旧转录"))
        db.add(KnowledgePoint(lesson_id=lesson.id, title="旧知识点", importance=1))
        db.add(Project(lesson_id=lesson.id, name="旧项目"))
        db.commit()
        self.lesson_id = lesson.id
        db.close()

    def tearDown(self):
        self.local_engine.dispose()

    def test_failed_analysis_preserves_previous_results(self):
        class FailingClient:
            def extract_knowledge_points(self, _text):
                raise RuntimeError("模拟 API 失败")

        with patch("app.ai.deepseek_client.DeepSeekClient", return_value=FailingClient()):
            run_analysis(self.session_factory, self.lesson_id)

        db = self.session_factory()
        try:
            self.assertEqual(db.query(KnowledgePoint).filter_by(lesson_id=self.lesson_id).count(), 1)
            self.assertEqual(db.query(Project).filter_by(lesson_id=self.lesson_id).count(), 1)
            self.assertEqual(db.get(Lesson, self.lesson_id).status, "completed")
        finally:
            db.close()

    def test_failed_transcription_preserves_previous_transcript(self):
        class FailingTranscriber:
            def transcribe(self, _path):
                raise RuntimeError("模拟 Whisper 失败")

        previous_root = settings.UPLOAD_DIR
        with tempfile.TemporaryDirectory() as temp_dir:
            settings.UPLOAD_DIR = temp_dir
            audio_dir = Path(temp_dir) / "audio" / str(self.lesson_id)
            audio_dir.mkdir(parents=True)
            (audio_dir / "old.wav").write_bytes(self._minimal_wav())
            try:
                run_transcription(self.session_factory, self.lesson_id, FailingTranscriber())
            finally:
                settings.UPLOAD_DIR = previous_root

        db = self.session_factory()
        try:
            transcripts = db.query(Transcript).filter_by(lesson_id=self.lesson_id).all()
            self.assertEqual([item.text for item in transcripts], ["旧转录"])
            self.assertEqual(db.get(Lesson, self.lesson_id).status, "uploaded")
        finally:
            db.close()

    def test_low_quality_transcription_preserves_previous_transcript(self):
        class RepeatingTranscriber:
            def transcribe(self, _path):
                segments = [
                    SimpleNamespace(
                        start=index * 20,
                        end=(index + 1) * 20,
                        text="Thank you.",
                    )
                    for index in range(25)
                ]
                return iter(segments), SimpleNamespace(duration=500, language="en")

        previous_root = settings.UPLOAD_DIR
        with tempfile.TemporaryDirectory() as temp_dir:
            settings.UPLOAD_DIR = temp_dir
            audio_dir = Path(temp_dir) / "audio" / str(self.lesson_id)
            audio_dir.mkdir(parents=True)
            (audio_dir / "old.wav").write_bytes(self._minimal_wav())
            try:
                run_transcription(
                    self.session_factory,
                    self.lesson_id,
                    RepeatingTranscriber(),
                )
            finally:
                settings.UPLOAD_DIR = previous_root

        db = self.session_factory()
        try:
            transcripts = db.query(Transcript).filter_by(lesson_id=self.lesson_id).all()
            self.assertEqual([item.text for item in transcripts], ["旧转录"])
            self.assertEqual(db.get(Lesson, self.lesson_id).status, "uploaded")
        finally:
            db.close()

    @staticmethod
    def _minimal_wav() -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            wav_file.writeframes(b"\x00\x00" * 80)
        return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
