# 数据模型包
# 导入所有模型类，确保 Base.metadata 能发现它们以自动建表

from .models import (
    Course,
    Chapter,
    Lesson,
    Transcript,
    KnowledgePoint,
    Project,
    KnowledgeProjectRelation,
)


__all__ = [
    "Course",
    "Chapter",
    "Lesson",
    "Transcript",
    "KnowledgePoint",
    "Project",
    "KnowledgeProjectRelation",
]