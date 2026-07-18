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

from sqlalchemy import Float, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


# =============================================================================
# 1. Course — 课程
# =============================================================================
class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="课程标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="课程描述")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, comment="创建时间"
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
        DateTime, default=datetime.utcnow, comment="创建时间"
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
# 7. KnowledgeProjectRelation — 知识点与项目关联
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
# 8. LessonProgress — 学习进度
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
        default=datetime.utcnow,
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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