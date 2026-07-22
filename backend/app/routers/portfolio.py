"""面试作品机会路由。"""

import logging
import io

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.portfolio import (
    PortfolioOpportunityResponse,
    PortfolioProjectResponse,
    PortfolioProjectTaskUpdate,
    PortfolioShowcaseUpdate,
    PortfolioEvidenceCreate,
    PortfolioExecutionPackageResponse,
    PortfolioCodeAnalysisResponse,
    PortfolioCodexAnalysisImport,
    PortfolioOverviewResponse,
)
from ..services import course_service
from ..services.portfolio_service import (
    generate_portfolio_opportunities,
    create_portfolio_project,
    get_portfolio_project,
    list_portfolio_opportunities,
    list_portfolio_projects,
    opportunity_to_dict,
    portfolio_project_to_dict,
    update_portfolio_project_task,
    update_portfolio_showcase,
    create_portfolio_evidence,
    delete_portfolio_evidence,
    generate_portfolio_execution_package,
    get_portfolio_execution_package,
    portfolio_execution_package_to_dict,
    build_portfolio_overview,
)
from ..services.execution_export_service import build_codex_handoff_archive
from ..services.codex_analysis_service import (
    code_analysis_to_dict,
    get_codex_code_analysis,
    import_codex_analysis,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["面试作品"])


@router.get(
    "/api/portfolio-overview",
    response_model=PortfolioOverviewResponse,
)
def get_portfolio_overview(db: Session = Depends(get_db)):
    """汇总所有项目的真实能力、验证结果与简历材料。"""
    return build_portfolio_overview(db)


@router.get(
    "/api/portfolio-projects",
    response_model=list[PortfolioProjectResponse],
)
def get_projects(db: Session = Depends(get_db)):
    """查询全部作品项目及当前完成进度。"""
    return [
        portfolio_project_to_dict(project)
        for project in list_portfolio_projects(db)
    ]


@router.get(
    "/api/chapters/{chapter_id}/portfolio-opportunities",
    response_model=list[PortfolioOpportunityResponse],
)
def get_portfolio_opportunities(
    chapter_id: int,
    db: Session = Depends(get_db),
):
    chapter = course_service.get_chapter(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return [
        opportunity_to_dict(item)
        for item in list_portfolio_opportunities(db, chapter_id)
    ]


@router.post(
    "/api/chapters/{chapter_id}/portfolio-opportunities/generate",
    response_model=list[PortfolioOpportunityResponse],
)
def create_portfolio_opportunities(
    chapter_id: int,
    db: Session = Depends(get_db),
):
    chapter = course_service.get_chapter(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    try:
        items = generate_portfolio_opportunities(db, chapter_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("章节作品机会生成失败: chapter_id=%d", chapter_id)
        raise HTTPException(status_code=502, detail="作品机会生成失败，请稍后重试") from exc

    return [opportunity_to_dict(item) for item in items]


@router.post(
    "/api/portfolio-opportunities/{opportunity_id}/create-project",
    response_model=PortfolioProjectResponse,
)
def create_project_from_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
):
    """将候选机会转换为正式作品项目蓝图。"""
    try:
        project = create_portfolio_project(db, opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("作品项目创建失败: opportunity_id=%d", opportunity_id)
        raise HTTPException(status_code=502, detail="作品项目创建失败，请稍后重试") from exc
    return portfolio_project_to_dict(project)


@router.get(
    "/api/portfolio-projects/{project_id}",
    response_model=PortfolioProjectResponse,
)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """查询正式作品项目蓝图。"""
    project = get_portfolio_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="作品项目不存在")
    return portfolio_project_to_dict(project)


@router.patch(
    "/api/portfolio-project-tasks/{task_id}",
    response_model=PortfolioProjectResponse,
)
def update_project_task(
    task_id: int,
    payload: PortfolioProjectTaskUpdate,
    db: Session = Depends(get_db),
):
    """更新开发任务状态，并返回联动后的项目。"""
    project = update_portfolio_project_task(db, task_id, payload.status)
    if not project:
        raise HTTPException(status_code=404, detail="作品项目任务不存在")
    return portfolio_project_to_dict(project)


@router.put(
    "/api/portfolio-projects/{project_id}/showcase",
    response_model=PortfolioProjectResponse,
)
def save_project_showcase(
    project_id: int,
    payload: PortfolioShowcaseUpdate,
    db: Session = Depends(get_db),
):
    """保存 GitHub、演示地址和项目讲解资料。"""
    try:
        project = update_portfolio_showcase(db, project_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not project:
        raise HTTPException(status_code=404, detail="作品项目不存在")
    return portfolio_project_to_dict(project)


@router.post(
    "/api/portfolio-projects/{project_id}/evidences",
    response_model=PortfolioProjectResponse,
)
def add_project_evidence(
    project_id: int,
    payload: PortfolioEvidenceCreate,
    db: Session = Depends(get_db),
):
    """新增代码、测试、文档或演示成果证据。"""
    try:
        project = create_portfolio_evidence(db, project_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not project:
        raise HTTPException(status_code=404, detail="作品项目不存在")
    return portfolio_project_to_dict(project)


@router.delete(
    "/api/portfolio-evidences/{evidence_id}",
    status_code=204,
)
def remove_project_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
):
    """删除成果证据。"""
    if not delete_portfolio_evidence(db, evidence_id):
        raise HTTPException(status_code=404, detail="成果证据不存在")
    return Response(status_code=204)


@router.get(
    "/api/portfolio-projects/{project_id}/execution-package",
    response_model=PortfolioExecutionPackageResponse | None,
)
def get_project_execution_package(
    project_id: int,
    db: Session = Depends(get_db),
):
    """查询项目执行包；尚未生成时返回 null。"""
    if not get_portfolio_project(db, project_id):
        raise HTTPException(status_code=404, detail="作品项目不存在")
    package = get_portfolio_execution_package(db, project_id)
    return portfolio_execution_package_to_dict(package) if package else None


@router.post(
    "/api/portfolio-projects/{project_id}/execution-package/generate",
    response_model=PortfolioExecutionPackageResponse,
)
def create_project_execution_package(
    project_id: int,
    db: Session = Depends(get_db),
):
    """生成或重新生成可交给 Codex 的项目执行包。"""
    try:
        package = generate_portfolio_execution_package(db, project_id)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("项目执行包生成失败: project_id=%d", project_id)
        raise HTTPException(status_code=502, detail="项目执行包生成失败，请稍后重试") from exc
    if not package:
        raise HTTPException(status_code=404, detail="作品项目不存在")
    return portfolio_execution_package_to_dict(package)


@router.get(
    "/api/portfolio-projects/{project_id}/execution-package/codex-zip",
)
def download_codex_handoff_package(
    project_id: int,
    db: Session = Depends(get_db),
):
    """下载可解压后直接交给 Codex 的项目资料 ZIP。"""
    try:
        archive = build_codex_handoff_archive(db, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        io.BytesIO(archive),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="portfolio-project-{project_id}-codex-handoff.zip"'
            )
        },
    )


@router.get(
    "/api/portfolio-projects/{project_id}/code-analysis",
    response_model=PortfolioCodeAnalysisResponse | None,
)
def get_code_analysis(
    project_id: int,
    db: Session = Depends(get_db),
):
    """查询已导入的 Codex 工作区代码分析。"""
    if not get_portfolio_project(db, project_id):
        raise HTTPException(status_code=404, detail="作品项目不存在")
    result = get_codex_code_analysis(db, project_id)
    return code_analysis_to_dict(*result) if result else None

@router.post(
    "/api/portfolio-projects/{project_id}/code-analysis/import",
    response_model=PortfolioCodeAnalysisResponse,
)
def import_code_analysis(
    project_id: int,
    payload: PortfolioCodexAnalysisImport,
    db: Session = Depends(get_db),
):
    """验证项目归属、结果结构和引用一致性后导入 Codex JSON。"""
    try:
        analysis = import_codex_analysis(db, project_id, payload.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = get_codex_code_analysis(db, project_id)
    if not result:
        raise HTTPException(status_code=500, detail="Codex 分析结果保存后校验失败")
    return code_analysis_to_dict(*result)
