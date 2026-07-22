"""验证并保存 Codex 在真实项目工作区生成的分析结果。"""

import json

from sqlalchemy.orm import Session

from ..models.models import (
    PortfolioCodeAnalysis,
    PortfolioCodexAnalysisMetadata,
    PortfolioLearningGuide,
)
from ..time_utils import utc_now
from .codex_analysis_contracts import analysis_request, analysis_result_schema
from .codex_analysis_normalizers import (
    derive_interview_showcase as _derive_interview_showcase,
    interview_showcase_for_response as _interview_showcase_for_response,
    json_dict as _json_dict,
    json_list as _json_list,
    json_records as _json_records,
    normalize_codex_result as _normalize_codex_result,
    validate_result_references as _validate_result_references,
)
from .portfolio_service import get_portfolio_project


def get_codex_code_analysis(
    db: Session,
    project_id: int,
) -> tuple[
    PortfolioCodeAnalysis,
    PortfolioCodexAnalysisMetadata,
    PortfolioLearningGuide | None,
] | None:
    analysis = (
        db.query(PortfolioCodeAnalysis)
        .filter(PortfolioCodeAnalysis.project_id == project_id)
        .first()
    )
    metadata = (
        db.query(PortfolioCodexAnalysisMetadata)
        .filter(PortfolioCodexAnalysisMetadata.project_id == project_id)
        .first()
    )
    guide = (
        db.query(PortfolioLearningGuide)
        .filter(PortfolioLearningGuide.project_id == project_id)
        .first()
    )
    return (analysis, metadata, guide) if analysis and metadata else None


def import_codex_analysis(
    db: Session,
    project_id: int,
    data: dict,
) -> PortfolioCodeAnalysis:
    """校验 Codex 回传结构及内部引用后保存分析结果。"""
    project = get_portfolio_project(db, project_id)
    if not project:
        raise LookupError("作品项目不存在")
    if data.get("project_id") != project_id:
        raise ValueError("分析结果属于其他作品项目，请检查 project_id")

    normalized = _normalize_codex_result(data, project.tasks)
    _validate_result_references(
        normalized,
        normalized["file_tree"],
        set(_json_list(project.knowledge_points)),
    )

    analysis = (
        db.query(PortfolioCodeAnalysis)
        .filter(PortfolioCodeAnalysis.project_id == project.id)
        .first()
    ) or PortfolioCodeAnalysis(project_id=project.id)
    analysis.original_filename = normalized["workspace_name"]
    analysis.archive_path = ""
    analysis.file_count = normalized["file_count"]
    analysis.source_size = normalized["source_size"]
    json_fields = (
        "file_tree",
        "key_files",
        "key_modules",
        "execution_flow",
        "knowledge_mapping",
        "plan_differences",
        "interview_demo",
        "interview_questions",
        "risks_and_limitations",
    )
    for field in json_fields:
        setattr(analysis, field, json.dumps(normalized[field], ensure_ascii=False))
    analysis.language_stats = json.dumps(
        normalized["language_stats"], ensure_ascii=False
    )
    for field in ("implementation_summary", "actual_architecture", "run_and_test"):
        setattr(analysis, field, normalized[field])
    analysis.interview_showcase = json.dumps(
        normalized["interview_showcase"], ensure_ascii=False
    )
    analysis.implementation_status = json.dumps(
        normalized["implementation_status"], ensure_ascii=False
    )
    analysis.updated_at = utc_now()
    task_results = normalized["implementation_status"].get("task_results", [])
    if task_results and all(item["status"] == "verified" for item in task_results):
        project.status = "completed"
    elif task_results:
        project.status = "in_progress"

    metadata = (
        db.query(PortfolioCodexAnalysisMetadata)
        .filter(PortfolioCodexAnalysisMetadata.project_id == project.id)
        .first()
    ) or PortfolioCodexAnalysisMetadata(project_id=project.id)
    metadata.source_fingerprint = normalized["source_fingerprint"]
    metadata.verification_evidence = json.dumps(
        normalized["verification_evidence"], ensure_ascii=False
    )
    metadata.imported_at = utc_now()

    guide = (
        db.query(PortfolioLearningGuide)
        .filter(PortfolioLearningGuide.project_id == project.id)
        .first()
    ) or PortfolioLearningGuide(project_id=project.id)
    guide.content = json.dumps(normalized["learning_guide"], ensure_ascii=False)
    guide.updated_at = utc_now()
    project.updated_at = utc_now()
    db.add_all([analysis, metadata, guide])
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return analysis


def code_analysis_to_dict(
    analysis: PortfolioCodeAnalysis,
    metadata: PortfolioCodexAnalysisMetadata,
    guide: PortfolioLearningGuide | None,
) -> dict:
    return {
        "id": analysis.id,
        "project_id": analysis.project_id,
        "original_filename": analysis.original_filename,
        "file_count": analysis.file_count,
        "source_size": analysis.source_size,
        "file_tree": _json_list(analysis.file_tree),
        "language_stats": _json_dict(analysis.language_stats),
        "key_files": _json_list(analysis.key_files),
        "implementation_summary": analysis.implementation_summary,
        "actual_architecture": analysis.actual_architecture,
        "key_modules": _json_records(analysis.key_modules),
        "execution_flow": _json_list(analysis.execution_flow),
        "knowledge_mapping": _json_records(analysis.knowledge_mapping),
        "plan_differences": _json_records(analysis.plan_differences),
        "run_and_test": analysis.run_and_test,
        "interview_demo": _json_list(analysis.interview_demo),
        "interview_questions": _json_records(analysis.interview_questions),
        "risks_and_limitations": _json_list(analysis.risks_and_limitations),
        "verification_evidence": _json_records(metadata.verification_evidence),
        "analysis_source": "codex",
        "source_fingerprint": metadata.source_fingerprint,
        "learning_guide": _json_dict(guide.content) if guide else None,
        "interview_showcase": _interview_showcase_for_response(analysis, metadata),
        "implementation_status": _json_dict(analysis.implementation_status),
        "created_at": analysis.created_at,
        "updated_at": analysis.updated_at,
    }
