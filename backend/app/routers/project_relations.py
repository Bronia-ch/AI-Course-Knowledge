"""
项目关联知识点路由

端点：
  GET /api/projects/{project_id}/knowledge-points  — 查询项目关联的知识点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models.models import Project, KnowledgeProjectRelation

router = APIRouter(prefix="/api/projects", tags=["项目关联"])


@router.get("/{project_id}/knowledge-points")
def get_project_knowledge_points(
    project_id: int,
    db: Session = Depends(get_db),
):
    """
    查询某个项目关联的所有知识点

    通过 KnowledgeProjectRelation 表查询，
    返回关联的知识点信息及关联原因。

    响应格式:
    [
      {
        "id": 1,
        "title": "反向传播算法",
        "description": "用于训练神经网络",
        "importance": 5,
        "category": "算法原理",
        "timestamp": 7,
        "reason": "该知识点用于训练项目模型"
      }
    ]
    """
    # ---- 验证项目存在 ----
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # ---- 查询关联关系 ----
    relations = (
        db.query(KnowledgeProjectRelation)
        .options(joinedload(KnowledgeProjectRelation.knowledge_point))
        .filter(KnowledgeProjectRelation.project_id == project_id)
        .all()
    )

    # ---- 组装响应（去重：同一知识点只返回一次）----
    result = []
    seen_kp_ids = set()
    for rel in relations:
        kp = rel.knowledge_point
        if kp.id in seen_kp_ids:
            continue  # 跳过重复知识点
        seen_kp_ids.add(kp.id)
        result.append({
            "id": kp.id,
            "title": kp.title,
            "description": kp.description,
            "importance": kp.importance,
            "category": kp.category,
            "timestamp": kp.timestamp,
            "reason": rel.reason,
        })

    return result
