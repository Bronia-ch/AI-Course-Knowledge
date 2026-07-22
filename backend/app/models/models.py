"""
AI课程知识库 - 数据库模型

本文件定义所有 ORM 模型，按依赖关系从上到下排列：
  Course → Chapter → Lesson → Transcript / KnowledgePoint / Project

技术约定：
  - 使用 SQLAlchemy 2.0 Mapped 语法
  - relationship 使用 back_populates 双向绑定
  - 父级关系设置 cascade="all, delete-orphan" 实现级联删除
"""

from __future__ import annotations  # 允许前向引用（List["Chapter"] 写法）

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, Float, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..time_utils import utc_now


# =============================================================================
# 1. Course — 课程
# =============================================================================
class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="课程标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="课程描述")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, comment="创建时间"
    )

    # ---- 关系 ----
    # 一个课程包含多个章节，删除课程时级联删除所有章节
    chapters: Mapped[List["Chapter"]] = relationship(
        "Chapter", back_populates="course", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Course(id={self.id}, title='{self.title}')>"


# =============================================================================
# 2. Chapter — 章节
# =============================================================================
class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id"), nullable=False, comment="所属课程ID"
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="章节标题")
    order_index: Mapped[int] = mapped_column(Integer, default=0, comment="排序序号")

    # ---- 关系 ----
    course: Mapped["Course"] = relationship("Course", back_populates="chapters")
    lessons: Mapped[List["Lesson"]] = relationship(
        "Lesson", back_populates="chapter", cascade="all, delete-orphan"
    )
    portfolio_opportunities: Mapped[List["PortfolioOpportunity"]] = relationship(
        "PortfolioOpportunity", back_populates="chapter"
    )
    portfolio_projects: Mapped[List["PortfolioProject"]] = relationship(
        "PortfolioProject", back_populates="chapter"
    )

    def __repr__(self) -> str:
        return f"<Chapter(id={self.id}, title='{self.title}', order={self.order_index})>"


# =============================================================================
# 3. Lesson — 课节
# =============================================================================
class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chapters.id"), nullable=False, comment="所属章节ID"
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="课节标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="课节描述")
    audio_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="音频文件路径"
    )
    duration: Mapped[int] = mapped_column(Integer, default=0, comment="音频时长（秒）")
    status: Mapped[str] = mapped_column(
        String(20), default="pending",
        comment="状态: pending / uploaded / processing / completed / analyzing / analyzed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, comment="创建时间"
    )

    # ---- 关系 ----
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="lessons")
    transcripts: Mapped[List["Transcript"]] = relationship(
        "Transcript", back_populates="lesson", cascade="all, delete-orphan"
    )
    knowledge_points: Mapped[List["KnowledgePoint"]] = relationship(
        "KnowledgePoint", back_populates="lesson", cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="lesson", cascade="all, delete-orphan"
    )
    portfolio_opportunities: Mapped[List["PortfolioOpportunity"]] = relationship(
        "PortfolioOpportunity", back_populates="lesson", cascade="all, delete-orphan"
    )
    progress: Mapped[Optional["LessonProgress"]] = relationship(
        "LessonProgress", back_populates="lesson", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Lesson(id={self.id}, title='{self.title}', status='{self.status}')>"

    @property
    def transcript_count(self) -> int:
        """转写片段数量（动态计算，非数据库列）"""
        return len(self.transcripts) if self.transcripts else 0

    @property
    def knowledge_point_count(self) -> int:
        """知识点数量（动态计算）"""
        return len(self.knowledge_points) if self.knowledge_points else 0

    @property
    def project_count(self) -> int:
        """项目数量（动态计算）"""
        return len(self.projects) if self.projects else 0


# =============================================================================
# 4. Transcript — 语音转写记录
# =============================================================================
class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lessons.id"), nullable=False, comment="所属课节ID"
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False, comment="片段起始时间（秒）")
    end_time: Mapped[float] = mapped_column(Float, nullable=False, comment="片段结束时间（秒）")
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="转写文本")

    # ---- 关系 ----
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="transcripts")

    def __repr__(self) -> str:
        preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"<Transcript(id={self.id}, [{self.start_time}s-{self.end_time}s] '{preview}')>"


# =============================================================================
# 5. KnowledgePoint — 知识点
# =============================================================================
class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lessons.id"), nullable=False, comment="所属课节ID"
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="知识点标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="知识点详细说明")
    timestamp: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="音频中对应时间（秒）"
    )
    importance: Mapped[int] = mapped_column(Integer, default=1, comment="重要程度 1-5")
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="分类标签")

    # ---- 关系 ----
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="knowledge_points")

    project_relations: Mapped[List["KnowledgeProjectRelation"]] = relationship(
        "KnowledgeProjectRelation",
        back_populates="knowledge_point",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<KnowledgePoint(id={self.id}, title='{self.title}', importance={self.importance})>"


# =============================================================================
# 6. Project — 项目分析
# =============================================================================
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lessons.id"), nullable=False, comment="所属课节ID"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="项目名称")
    goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="项目目标")
    input: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="输入说明")
    output: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="输出说明")
    technology_stack: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="技术栈（JSON 字符串）"
    )
    workflow: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="工作流程（JSON 字符串）")

    # ---- 关系 ----
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="projects")

    knowledge_relations: Mapped[List["KnowledgeProjectRelation"]] = relationship(
        "KnowledgeProjectRelation",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}')>"


# =============================================================================
# 7. PortfolioOpportunity — 面试作品机会
# =============================================================================
class PortfolioOpportunity(Base):
    __tablename__ = "portfolio_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lessons.id"),
        nullable=False,
        index=True,
        comment="来源课节ID",
    )
    chapter_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("chapters.id"),
        nullable=True,
        index=True,
        comment="来源章节ID；旧课节成果为空",
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    project_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="micro_demo / topic_project / flagship_project",
    )
    ability_claim: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_points: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="覆盖知识点标题 JSON 数组",
    )
    core_features: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="核心功能 JSON 数组",
    )
    interview_value: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_effort: Mapped[str] = mapped_column(String(100), nullable=False)
    recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    lesson: Mapped["Lesson"] = relationship(
        "Lesson",
        back_populates="portfolio_opportunities",
    )
    chapter: Mapped[Optional["Chapter"]] = relationship(
        "Chapter",
        back_populates="portfolio_opportunities",
    )
    portfolio_project: Mapped[Optional["PortfolioProject"]] = relationship(
        "PortfolioProject",
        back_populates="opportunity",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<PortfolioOpportunity(id={self.id}, title='{self.title}')>"


# =============================================================================
# 8. PortfolioProject — 正式作品项目
# =============================================================================
class PortfolioProject(Base):
    __tablename__ = "portfolio_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolio_opportunities.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    lesson_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lessons.id"),
        nullable=False,
        index=True,
    )
    chapter_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("chapters.id"),
        nullable=True,
        index=True,
        comment="来源章节ID；旧课节项目为空",
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    project_type: Mapped[str] = mapped_column(String(30), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    use_case: Mapped[str] = mapped_column(Text, nullable=False)
    architecture: Mapped[str] = mapped_column(Text, nullable=False)
    technology_stack: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    core_features: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    knowledge_points: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    deliverables: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    interview_pitch: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_effort: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planning")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    opportunity: Mapped["PortfolioOpportunity"] = relationship(
        "PortfolioOpportunity",
        back_populates="portfolio_project",
    )
    chapter: Mapped[Optional["Chapter"]] = relationship(
        "Chapter",
        back_populates="portfolio_projects",
    )
    tasks: Mapped[List["PortfolioProjectTask"]] = relationship(
        "PortfolioProjectTask",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="PortfolioProjectTask.order_index",
    )
    showcase: Mapped[Optional["PortfolioProjectShowcase"]] = relationship(
        "PortfolioProjectShowcase",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )
    evidences: Mapped[List["PortfolioProjectEvidence"]] = relationship(
        "PortfolioProjectEvidence",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="PortfolioProjectEvidence.created_at.desc()",
    )
    execution_package: Mapped[Optional["PortfolioExecutionPackage"]] = relationship(
        "PortfolioExecutionPackage",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )
    code_analysis: Mapped[Optional["PortfolioCodeAnalysis"]] = relationship(
        "PortfolioCodeAnalysis",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )
    submission: Mapped[Optional["PortfolioProjectSubmission"]] = relationship(
        "PortfolioProjectSubmission",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )
    codex_analysis_metadata: Mapped[
        Optional["PortfolioCodexAnalysisMetadata"]
    ] = relationship(
        "PortfolioCodexAnalysisMetadata",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )
    learning_guide: Mapped[Optional["PortfolioLearningGuide"]] = relationship(
        "PortfolioLearningGuide",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )


# =============================================================================
# 9. PortfolioProjectTask — 作品项目任务
# =============================================================================
class PortfolioProjectTask(Base):
    __tablename__ = "portfolio_project_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolio_projects.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")

    project: Mapped["PortfolioProject"] = relationship(
        "PortfolioProject",
        back_populates="tasks",
    )
    evidences: Mapped[List["PortfolioProjectEvidence"]] = relationship(
        "PortfolioProjectEvidence",
        back_populates="task",
    )


# =============================================================================
# 10. PortfolioProjectShowcase — 作品展示资料
# =============================================================================
class PortfolioProjectShowcase(Base):
    __tablename__ = "portfolio_project_showcases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolio_projects.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    demo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    demo_video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    screenshot_urls: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    highlights: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    technical_challenges: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    project: Mapped["PortfolioProject"] = relationship(
        "PortfolioProject",
        back_populates="showcase",
    )


# =============================================================================
# 11. PortfolioProjectEvidence — 项目成果证据
# =============================================================================
class PortfolioProjectEvidence(Base):
    __tablename__ = "portfolio_project_evidences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolio_projects.id"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("portfolio_project_tasks.id"),
        nullable=True,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    project: Mapped["PortfolioProject"] = relationship(
        "PortfolioProject",
        back_populates="evidences",
    )
    task: Mapped[Optional["PortfolioProjectTask"]] = relationship(
        "PortfolioProjectTask",
        back_populates="evidences",
    )


# =============================================================================
# 12. PortfolioExecutionPackage — 可交给开发型 AI 的项目执行包
# =============================================================================
class PortfolioExecutionPackage(Base):
    __tablename__ = "portfolio_execution_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolio_projects.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    project_brief: Mapped[str] = mapped_column(Text, nullable=False)
    technology_choices: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    architecture: Mapped[str] = mapped_column(Text, nullable=False)
    directory_structure: Mapped[str] = mapped_column(Text, nullable=False)
    data_models: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    api_contracts: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    implementation_phases: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    test_plan: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    acceptance_checklist: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    readme_requirements: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    codex_master_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    review_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    project: Mapped["PortfolioProject"] = relationship(
        "PortfolioProject",
        back_populates="execution_package",
    )


# =============================================================================
# 13. PortfolioCodeAnalysis — Codex 完成项目的真实代码分析
# =============================================================================
class PortfolioCodeAnalysis(Base):
    __tablename__ = "portfolio_code_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolio_projects.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    archive_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_tree: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    language_stats: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    key_files: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    implementation_summary: Mapped[str] = mapped_column(Text, nullable=False)
    actual_architecture: Mapped[str] = mapped_column(Text, nullable=False)
    key_modules: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    execution_flow: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    knowledge_mapping: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    plan_differences: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    run_and_test: Mapped[str] = mapped_column(Text, nullable=False)
    interview_demo: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    interview_questions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    risks_and_limitations: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    interview_showcase: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    implementation_status: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    project: Mapped["PortfolioProject"] = relationship(
        "PortfolioProject",
        back_populates="code_analysis",
    )


# =============================================================================
# 14. PortfolioProjectSubmission — 完成项目安全扫描记录
# =============================================================================
class PortfolioProjectSubmission(Base):
    __tablename__ = "portfolio_project_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolio_projects.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    archive_path: Mapped[str] = mapped_column(String(500), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_tree: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    language_stats: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    key_files: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    project: Mapped["PortfolioProject"] = relationship(
        "PortfolioProject",
        back_populates="submission",
    )


# =============================================================================
# 15. PortfolioCodexAnalysisMetadata — Codex 回传验证信息
# =============================================================================
class PortfolioCodexAnalysisMetadata(Base):
    __tablename__ = "portfolio_codex_analysis_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolio_projects.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_evidence: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    project: Mapped["PortfolioProject"] = relationship(
        "PortfolioProject",
        back_populates="codex_analysis_metadata",
    )


# =============================================================================
# PortfolioLearningGuide — 面向初学者的连续项目学习指南
# =============================================================================
class PortfolioLearningGuide(Base):
    __tablename__ = "portfolio_learning_guides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolio_projects.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
    )
    project: Mapped["PortfolioProject"] = relationship(
        "PortfolioProject",
        back_populates="learning_guide",
    )


# =============================================================================
# 16. KnowledgeProjectRelation — 知识点与项目关联
# =============================================================================

class KnowledgeProjectRelation(Base):
    __tablename__ = "knowledge_project_relations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    knowledge_point_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("knowledge_points.id"),
        nullable=False,
        comment="知识点ID"
    )

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False,
        comment="项目ID"
    )

    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="关联原因"
    )

    # ---- 关系 ----

    knowledge_point: Mapped["KnowledgePoint"] = relationship(
        "KnowledgePoint",
        back_populates="project_relations"
    )

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="knowledge_relations"
    )


# =============================================================================
# 11. LessonProgress — 学习进度
# =============================================================================

class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    lesson_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lessons.id"),
        nullable=False,
        comment="课节ID",
    )

    current_time: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="当前播放时间（秒）",
    )

    completed_knowledge_points: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="已完成知识点ID列表（JSON数组，如 [1,3,5]）",
    )

    progress_percent: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="学习进度百分比 0-100",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        comment="更新时间",
    )

    # ---- 关系 ----
    lesson: Mapped["Lesson"] = relationship(
        "Lesson",
        back_populates="progress",
    )

    def __repr__(self) -> str:
        return (
            f"<LessonProgress(id={self.id}, lesson_id={self.lesson_id}, "
            f"percent={self.progress_percent}%)>"
        )
