"""收尾阶段的关键数据安全回归测试。"""

import asyncio
import io
import json
import tempfile
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
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
    paths,
    validate_result_references,
)
from app.services.upload_service import save_audio_file
from app.services.analysis_service import run_analysis
from app.services.transcription_service import run_transcription
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
from app.services.portfolio_serializers import (
    opportunity_to_dict,
    portfolio_execution_package_to_dict,
    portfolio_project_to_dict,
    project_implementation_status,
)
from app.time_utils import utc_now


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
            "codex_master_prompt": "开发提示",
            "review_prompt": "审查提示",
            "explanation_prompt": "讲解提示",
            "implementation_phases": [
                {"title": f"阶段 {index}", "codex_prompt": "执行"}
                for index in range(9)
            ],
        }
        normalized = normalize_execution_package(base)
        self.assertEqual(normalized["directory_structure"], "src/")
        self.assertEqual(len(normalized["implementation_phases"]), 7)

        with self.assertRaises(ValueError):
            normalize_execution_package({**base, "review_prompt": ""})


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
