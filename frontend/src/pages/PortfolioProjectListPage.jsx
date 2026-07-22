import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Breadcrumb from "../components/Breadcrumb";
import { portfolioAPI } from "../services/api";
import "./PortfolioProjectListPage.css";

const projectTypeLabels = {
  micro_demo: "微型 Demo",
  topic_project: "专题项目",
  flagship_project: "旗舰项目",
};

const projectStatusLabels = {
  planning: "规划中",
  in_progress: "开发中",
  completed: "已完成",
};

const implementationStatusLabels = {
  pending_analysis: "待代码分析",
  not_verified: "待验证",
  partial: "部分验证",
  verified: "已验证",
};

export default function PortfolioProjectListPage() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    portfolioAPI.listProjects()
      .then(setProjects)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">加载作品项目...</div>;
  if (error) return <div className="error">加载失败: {error}</div>;

  return (
    <div className="page portfolio-list-page">
      <Breadcrumb items={[{ label: "课程列表", to: "/" }, { label: "我的作品" }]} />
      <div className="page-header">
        <div>
          <h1>我的作品</h1>
          <p>把课程知识落实为可开发、可验收、可向面试官展示的项目。</p>
        </div>
        <Link className="btn btn-primary" to="/portfolio-overview">查看个人能力作品集</Link>
      </div>

      {projects.length === 0 ? (
        <section className="card portfolio-list-empty">
          <strong>还没有作品项目</strong>
          <p>完成一个章节内所有课节的转录与知识分析，然后生成章节作品机会。</p>
          <Link className="btn btn-primary" to="/">返回课程列表</Link>
        </section>
      ) : (
        <div className="portfolio-list-grid">
          {projects.map((project) => {
            const actual = project.implementation_status;
            const hasAnalysis = actual.analysis_available;
            const progress = hasAnalysis ? actual.completion_percent : project.progress_percent;
            const statusClass = hasAnalysis ? actual.overall_status : project.status;
            return <article className="card portfolio-list-card" key={project.id}>
              <div className="portfolio-list-card-meta">
                <span>{projectTypeLabels[project.project_type]}</span>
                <strong className={statusClass}>
                  {hasAnalysis ? implementationStatusLabels[actual.overall_status] : (projectStatusLabels[project.status] || project.status)}
                </strong>
              </div>
              <h2>{project.title}</h2>
              <p>{project.objective}</p>
              <small>{project.chapter_id ? `来源章节：${project.chapter_title}` : `旧版来源课节 #${project.lesson_id}`} · {project.estimated_effort}</small>
              <div className="portfolio-list-progress-label">
                <span>{hasAnalysis ? "真实实现进度" : "计划任务进度"}</span>
                <strong>{progress}%</strong>
              </div>
              <div className="portfolio-list-progress">
                <span style={{ width: `${progress}%` }} />
              </div>
              <Link className="btn btn-primary" to={`/portfolio-projects/${project.id}`}>
                查看项目工作台
              </Link>
            </article>;
          })}
        </div>
      )}
    </div>
  );
}
