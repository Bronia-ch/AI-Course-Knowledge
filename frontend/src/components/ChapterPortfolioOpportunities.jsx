import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { portfolioAPI } from "../services/api";
import "./ChapterPortfolioOpportunities.css";

const projectTypeLabels = {
  micro_demo: "微型 Demo",
  topic_project: "专题项目",
  flagship_project: "旗舰项目",
};

export default function ChapterPortfolioOpportunities({ chapterId, lessons = [] }) {
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [creatingId, setCreatingId] = useState(null);
  const [error, setError] = useState(null);

  const incompleteLessons = lessons.filter(
    (lesson) => lesson.status !== "analyzed" || lesson.knowledge_point_count === 0,
  );

  const loadOpportunities = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setOpportunities(await portfolioAPI.listOpportunities(chapterId));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [chapterId]);

  useEffect(() => {
    loadOpportunities();
  }, [loadOpportunities]);

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      setOpportunities(await portfolioAPI.generateOpportunities(chapterId));
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleCreateProject = async (opportunity) => {
    if (opportunity.portfolio_project_id) {
      navigate(`/portfolio-projects/${opportunity.portfolio_project_id}/learn`);
      return;
    }
    try {
      setCreatingId(opportunity.id);
      setError(null);
      const project = await portfolioAPI.createProject(opportunity.id);
      await portfolioAPI.generateConceptGuide(project.id);
      navigate(`/portfolio-projects/${project.id}/learn`);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingId(null);
    }
  };

  return (
    <section className="chapter-portfolio">
      <div className="chapter-portfolio-header">
        <div>
          <small>CHAPTER PORTFOLIO</small>
          <h3>本章可展示成果</h3>
          <p>按顺序整合本章 {lessons.length} 节课的全部转录和知识点，生成完整作品方向。</p>
        </div>
        <button className="btn btn-primary btn-sm" onClick={handleGenerate} disabled={generating || lessons.length === 0 || incompleteLessons.length > 0}>
          {generating ? "正在分析整章内容..." : opportunities.length > 0 ? "重新生成" : "生成本章成果"}
        </button>
      </div>

      {incompleteLessons.length > 0 && (
        <div className="chapter-portfolio-readiness">
          <strong>完成以下课节后才能生成：</strong>
          {incompleteLessons.map((lesson) => <span key={lesson.id}>{lesson.title}</span>)}
        </div>
      )}
      {error && <div className="chapter-portfolio-error">{error}</div>}

      {loading ? (
        <div className="chapter-portfolio-empty">正在加载章节成果...</div>
      ) : opportunities.length === 0 ? (
        <div className="chapter-portfolio-empty">本章所有课节完成转录和知识分析后，即可生成综合项目。</div>
      ) : (
        <div className="chapter-portfolio-list">
          {opportunities.map((opportunity) => (
            <article className={`chapter-portfolio-card${opportunity.recommended ? " recommended" : ""}`} key={opportunity.id}>
              <div className="chapter-portfolio-title">
                <div><span>{projectTypeLabels[opportunity.project_type]}</span>{opportunity.recommended && <strong>推荐作品</strong>}{opportunity.learning_count > 0 && <span className="chapter-portfolio-learning-count">已学习 {opportunity.learning_count} 次</span>}</div>
                <h4>{opportunity.title}</h4>
              </div>
              <p className="chapter-portfolio-ability"><b>能力证明：</b>{opportunity.ability_claim}</p>
              <p>{opportunity.description}</p>
              <div className="chapter-portfolio-section"><b>综合课节</b><div className="chapter-portfolio-tags">{opportunity.covered_lessons.map((lesson) => <span key={lesson.id}>{lesson.title}</span>)}</div></div>
              <div className="chapter-portfolio-section"><b>覆盖知识</b><div className="chapter-portfolio-tags">{opportunity.knowledge_points.map((point) => <span key={point}>{point}</span>)}</div></div>
              <div className="chapter-portfolio-section"><b>核心功能</b><ul>{opportunity.core_features.map((feature) => <li key={feature}>{feature}</li>)}</ul></div>
              <div className="chapter-portfolio-value"><div><b>面试价值</b><p>{opportunity.interview_value}</p></div><span>{opportunity.estimated_effort}</span></div>
              <div className="chapter-portfolio-actions"><button className="btn btn-primary btn-sm" onClick={() => handleCreateProject(opportunity)} disabled={creatingId === opportunity.id}>{creatingId === opportunity.id ? "正在生成学习指南..." : opportunity.portfolio_project_id ? "查看作品学习指南" : "转为作品并学习"}</button></div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
