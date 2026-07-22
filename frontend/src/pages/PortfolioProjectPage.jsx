import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Breadcrumb from "../components/Breadcrumb";
import PortfolioEvidence from "../components/PortfolioEvidence";
import { portfolioAPI } from "../services/api";
import "./PortfolioProjectPage.css";

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

const taskStatusLabels = {
  pending: "待开始",
  in_progress: "进行中",
  completed: "已完成",
};

const implementationStatusLabels = {
  pending_analysis: "待代码分析",
  not_verified: "待验证",
  partial: "部分验证",
  verified: "已验证",
};

const taskResultLabels = {
  verified: "已验证",
  partial: "部分完成",
  not_verified: "未验证",
};

export default function PortfolioProjectPage() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updatingTaskId, setUpdatingTaskId] = useState(null);

  const updateTask = async (taskId, status) => {
    try {
      setUpdatingTaskId(taskId);
      setError(null);
      const data = await portfolioAPI.updateTask(taskId, status);
      setProject(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdatingTaskId(null);
    }
  };

  useEffect(() => {
    let active = true;
    portfolioAPI.getProject(Number(id))
      .then((data) => {
        if (active) setProject(data);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  if (loading) return <div className="loading">加载项目计划...</div>;
  if (error) return <div className="error">加载失败: {error}</div>;
  if (!project) return <div className="error">作品项目不存在</div>;

  const actualStatus = project.implementation_status;
  const usesCodexStatus = actualStatus.analysis_available;
  const displayedProgress = usesCodexStatus
    ? actualStatus.completion_percent
    : project.progress_percent;
  const taskResults = new Map(
    actualStatus.task_results.map((item) => [item.task_id, item]),
  );

  return (
    <div className="page portfolio-project-page">
      <Breadcrumb
        items={[
          { label: "课程列表", to: "/" },
          { label: "我的作品", to: "/portfolio-projects" },
          project.chapter_id
            ? { label: `来源章节：${project.chapter_title}`, to: `/courses/${project.course_id}#chapter-${project.chapter_id}` }
            : { label: "来源课节", to: `/lessons/${project.lesson_id}` },
          { label: project.title },
        ]}
      />

      <header className="portfolio-project-hero">
        <div className="portfolio-project-badges">
          <span>{projectTypeLabels[project.project_type]}</span>
          <strong>{usesCodexStatus ? implementationStatusLabels[actualStatus.overall_status] : (projectStatusLabels[project.status] || project.status)}</strong>
        </div>
        <div className="portfolio-project-links">
          <Link to={`/portfolio-projects/${project.id}/execution`}>
            AI 项目执行包
          </Link>
          <Link to={`/portfolio-projects/${project.id}/showcase`}>
            面试展示页
          </Link>
          <Link to={`/portfolio-projects/${project.id}/code-analysis`}>
            真实代码讲解
          </Link>
        </div>
        <h1>{project.title}</h1>
        <p>{project.objective}</p>
        {project.covered_lessons.length > 0 && (
          <div className="portfolio-project-source-lessons">
            <span>综合课节：</span>{project.covered_lessons.map((lesson) => <b key={lesson.id}>{lesson.title}</b>)}
          </div>
        )}
        <small>预计工作量：{project.estimated_effort}</small>
        <div className="portfolio-project-progress">
          <div>
            <span>{usesCodexStatus ? "真实实现进度" : "计划任务进度"}</span>
            <strong>{usesCodexStatus ? `${actualStatus.verified_task_count} 项已验证 · ${displayedProgress}%` : `${project.completed_task_count}/${project.task_count} 项 · ${displayedProgress}%`}</strong>
          </div>
          <div className="portfolio-project-progress-track">
            <span style={{ width: `${displayedProgress}%` }} />
          </div>
        </div>
      </header>

      {usesCodexStatus && (
        <section className={`card implementation-status-note ${actualStatus.overall_status}`}>
          <div>
            <span>CODEX REALITY CHECK</span>
            <strong>{implementationStatusLabels[actualStatus.overall_status]}</strong>
          </div>
          <p>{actualStatus.summary}</p>
          {actualStatus.legacy_derived && <small>当前结果来自旧版 JSON 的保守推导；以后使用新版执行包回传时，会自动逐项核对全部计划任务。</small>}
        </section>
      )}

      <section className="portfolio-project-grid">
        <article className="card">
          <h2>使用场景</h2>
          <p>{project.use_case}</p>
        </article>
        <article className="card">
          <h2>系统架构</h2>
          <p>{project.architecture}</p>
        </article>
      </section>

      <section className="card portfolio-project-section">
        <h2>技术栈</h2>
        <div className="portfolio-project-tags">
          {project.technology_stack.map((technology) => (
            <span key={technology}>{technology}</span>
          ))}
        </div>
      </section>

      <section className="portfolio-project-grid">
        <article className="card portfolio-project-section">
          <h2>核心功能</h2>
          <ul>
            {project.core_features.map((feature) => <li key={feature}>{feature}</li>)}
          </ul>
        </article>
        <article className="card portfolio-project-section">
          <h2>课程知识覆盖</h2>
          <div className="portfolio-project-tags knowledge">
            {project.knowledge_points.map((point) => <span key={point}>{point}</span>)}
          </div>
        </article>
      </section>

      <section className="card portfolio-project-section">
        <h2>开发任务</h2>
        <ol className="portfolio-project-tasks">
          {project.tasks.map((task) => (
            <li key={task.id}>
              <div>
                <strong>{task.title}</strong>
                <span className={`task-status ${usesCodexStatus ? (taskResults.get(task.id)?.status || "awaiting_review") : task.status}`}>
                  {usesCodexStatus
                    ? (taskResultLabels[taskResults.get(task.id)?.status] || "待新版分析核对")
                    : (taskStatusLabels[task.status] || task.status)}
                </span>
              </div>
              <p>{task.description}</p>
              <small>完成标准：{task.acceptance_criteria}</small>
              {taskResults.get(task.id) && (
                <div className="task-actual-result">
                  <p>{taskResults.get(task.id).explanation}</p>
                  <div>{taskResults.get(task.id).evidence_files.map((file) => <code key={file}>{file}</code>)}</div>
                </div>
              )}
              {!usesCodexStatus && <div className="portfolio-task-actions">
                {task.status !== "in_progress" && (
                  <button
                    className="btn btn-secondary btn-sm"
                    disabled={updatingTaskId === task.id}
                    onClick={() => updateTask(task.id, "in_progress")}
                  >
                    开始任务
                  </button>
                )}
                {task.status !== "completed" && (
                  <button
                    className="btn btn-success btn-sm"
                    disabled={updatingTaskId === task.id}
                    onClick={() => updateTask(task.id, "completed")}
                  >
                    标记完成
                  </button>
                )}
                {task.status !== "pending" && (
                  <button
                    className="btn btn-secondary btn-sm"
                    disabled={updatingTaskId === task.id}
                    onClick={() => updateTask(task.id, "pending")}
                  >
                    重新打开
                  </button>
                )}
              </div>}
            </li>
          ))}
        </ol>
      </section>

      <section className="portfolio-project-grid">
        <article className="card portfolio-project-section">
          <h2>项目交付物</h2>
          <ul>
            {project.deliverables.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </article>
        <article className="card portfolio-project-section">
          <h2>项目验收标准</h2>
          <ul>
            {project.acceptance_criteria.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </article>
      </section>

      <section className="card portfolio-project-section interview-pitch">
        <h2>面试讲解思路</h2>
        <p>{project.interview_pitch}</p>
      </section>

      <PortfolioEvidence project={project} onProjectChange={setProject} />
    </div>
  );
}
