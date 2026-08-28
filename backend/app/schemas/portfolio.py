"""面试作品机会 Schema。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PortfolioOpportunityResponse(BaseModel):
    id: int
    lesson_id: int
    chapter_id: int | None = None
    source_scope: Literal["lesson", "chapter"]
    covered_lessons: list[dict] = Field(default_factory=list)
    title: str
    project_type: Literal["micro_demo", "topic_project", "flagship_project"]
    ability_claim: str
    description: str
    knowledge_points: list[str]
    core_features: list[str]
    interview_value: str
    estimated_effort: str
    recommended: bool
    created_at: datetime
    portfolio_project_id: int | None = None
    learning_count: int = 0


class PortfolioProjectTaskResponse(BaseModel):
    id: int
    title: str
    description: str
    acceptance_criteria: str
    order_index: int
    status: str


class PortfolioProjectTaskUpdate(BaseModel):
    status: Literal["pending", "in_progress", "completed"]


class PortfolioLearningCompletionResponse(BaseModel):
    project_id: int
    learning_count: int


class PortfolioShowcaseUpdate(BaseModel):
    github_url: str | None = None
    demo_url: str | None = None
    demo_video_url: str | None = None
    screenshot_urls: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    technical_challenges: str | None = None


class PortfolioShowcaseResponse(PortfolioShowcaseUpdate):
    id: int | None = None
    updated_at: datetime | None = None


class PortfolioEvidenceCreate(BaseModel):
    evidence_type: Literal[
        "code", "test", "performance", "screenshot", "document", "demo", "other"
    ]
    title: str
    description: str | None = None
    url: str | None = None
    task_id: int | None = None


class PortfolioEvidenceResponse(PortfolioEvidenceCreate):
    id: int
    created_at: datetime
    task_title: str | None = None


class PortfolioCompletenessResponse(BaseModel):
    score: int
    completed_item_count: int
    total_item_count: int
    missing_items: list[str]


class PortfolioOverviewResponse(BaseModel):
    summary: dict
    introduction: str
    capabilities: list[dict] = Field(default_factory=list)
    technologies: list[dict] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    interview_order: list[dict] = Field(default_factory=list)
    markdown_content: str


class PortfolioExecutionPackageResponse(BaseModel):
    id: int
    project_id: int
    project_brief: str
    technology_choices: list[dict]
    architecture: str
    directory_structure: str
    data_models: list[dict]
    api_contracts: list[dict]
    implementation_phases: list[dict]
    test_plan: list[str]
    acceptance_checklist: list[str]
    readme_requirements: list[str]
    codex_master_prompt: str
    review_prompt: str
    explanation_prompt: str
    markdown_content: str
    created_at: datetime
    updated_at: datetime


class PortfolioCodeAnalysisResponse(BaseModel):
    id: int
    project_id: int
    original_filename: str
    file_count: int
    source_size: int
    file_tree: list[str]
    language_stats: dict[str, int]
    key_files: list[str]
    implementation_summary: str
    actual_architecture: str
    key_modules: list[dict]
    execution_flow: list[str]
    knowledge_mapping: list[dict]
    plan_differences: list[dict]
    run_and_test: str
    interview_demo: list[str]
    interview_questions: list[dict]
    risks_and_limitations: list[str]
    verification_evidence: list[dict]
    analysis_source: Literal["codex"]
    source_fingerprint: str
    learning_guide: dict | None = None
    interview_showcase: dict = Field(default_factory=dict)
    implementation_status: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class PortfolioConceptGuideResponse(BaseModel):
    id: int
    project_id: int
    content: dict
    reference_sources: list[dict] = Field(default_factory=list)
    reference_status: Literal["found", "not_found", "search_failed"]
    created_at: datetime
    updated_at: datetime


class PortfolioCodexProjectBlueprintImport(BaseModel):
    title: str
    objective: str
    use_case: str
    architecture: str
    technology_stack: list[str] = Field(default_factory=list)
    core_features: list[str] = Field(default_factory=list)
    knowledge_points: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    interview_pitch: str
    estimated_effort: str
    tasks: list[dict] = Field(default_factory=list)


class PortfolioCodexConceptGuideImport(BaseModel):
    content: dict
    reference_sources: list[dict] = Field(default_factory=list)
    reference_status: Literal["found", "not_found", "search_failed"] = "not_found"


class PortfolioProjectSubmissionResponse(BaseModel):
    id: int
    project_id: int
    original_filename: str
    source_fingerprint: str
    file_count: int
    source_size: int
    file_tree: list[str]
    language_stats: dict[str, int]
    key_files: list[str]
    created_at: datetime
    updated_at: datetime


class PortfolioCodexAnalysisImport(BaseModel):
    project_id: int
    workspace_name: str
    source_fingerprint: str
    file_count: int
    source_size: int
    file_tree: list[str] = Field(default_factory=list)
    language_stats: dict[str, int] = Field(default_factory=dict)
    key_files: list[str] = Field(default_factory=list)
    implementation_summary: str
    actual_architecture: str
    key_modules: list[dict] = Field(default_factory=list)
    execution_flow: list[str] = Field(default_factory=list)
    knowledge_mapping: list[dict] = Field(default_factory=list)
    plan_differences: list[dict] = Field(default_factory=list)
    run_and_test: str
    verification_evidence: list[dict] = Field(default_factory=list)
    interview_demo: list[str] = Field(default_factory=list)
    interview_questions: list[dict] = Field(default_factory=list)
    risks_and_limitations: list[str] = Field(default_factory=list)
    learning_guide: dict
    interview_showcase: dict | None = None
    implementation_status: dict | None = None


class PortfolioProjectResponse(BaseModel):
    id: int
    opportunity_id: int
    lesson_id: int
    chapter_id: int | None = None
    chapter_title: str | None = None
    course_id: int | None = None
    covered_lessons: list[dict] = Field(default_factory=list)
    title: str
    project_type: Literal["micro_demo", "topic_project", "flagship_project"]
    objective: str
    use_case: str
    architecture: str
    technology_stack: list[str]
    core_features: list[str]
    knowledge_points: list[str]
    deliverables: list[str]
    acceptance_criteria: list[str]
    interview_pitch: str
    estimated_effort: str
    status: str
    learning_count: int = 0
    created_at: datetime
    updated_at: datetime
    task_count: int
    completed_task_count: int
    progress_percent: float
    implementation_status: dict = Field(default_factory=dict)
    concept_guide_available: bool = False
    tasks: list[PortfolioProjectTaskResponse]
    showcase: PortfolioShowcaseResponse
    evidences: list[PortfolioEvidenceResponse]
    completeness: PortfolioCompletenessResponse
