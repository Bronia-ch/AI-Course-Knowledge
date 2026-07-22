import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Breadcrumb from "../components/Breadcrumb";
import { portfolioAPI } from "../services/api";
import "./PortfolioOverviewPage.css";

const statusLabels = {
  verified: "已验证",
  partial: "部分验证",
  not_verified: "待验证",
  pending_analysis: "待代码分析",
};

export default function PortfolioOverviewPage() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    portfolioAPI.getOverview()
      .then(setOverview)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const copyMarkdown = async () => {
    await navigator.clipboard.writeText(overview.markdown_content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  const downloadMarkdown = () => {
    const blob = new Blob([overview.markdown_content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "portfolio-overview.md";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <div className="loading">正在汇总真实项目能力...</div>;
  if (error) return <div className="error">加载失败: {error}</div>;

  const { summary } = overview;

  return (
    <div className="page portfolio-overview-page">
      <Breadcrumb items={[{ label: "课程列表", to: "/" }, { label: "我的作品", to: "/portfolio-projects" }, { label: "个人能力作品集" }]} />

      <header className="portfolio-overview-hero">
        <div>
          <small>VERIFIED PORTFOLIO</small>
          <h1>个人能力作品集</h1>
          <p>{overview.introduction}</p>
        </div>
        <div className="portfolio-overview-actions">
          <button className="btn btn-primary" onClick={copyMarkdown}>{copied ? "已复制" : "复制 Markdown"}</button>
          <button className="btn btn-secondary" onClick={downloadMarkdown}>下载 .md</button>
        </div>
      </header>

      <section className="portfolio-overview-stats">
        <article><strong>{summary.analyzed_project_count}/{summary.project_count}</strong><span>已完成真实代码分析</span></article>
        <article><strong>{summary.capability_count}</strong><span>带代码证据的能力</span></article>
        <article><strong>{summary.passed_check_count}</strong><span>通过的构建与测试</span></article>
        <article><strong>{summary.verified_project_count + summary.partial_project_count}</strong><span>已有真实实现证据的项目</span></article>
      </section>

      <section className="card portfolio-overview-section">
        <div className="portfolio-overview-heading">
          <div><small>CODE EVIDENCE</small><h2>已验证技术能力</h2></div>
          <p>这里只统计 Codex 在真实项目文件中找到代码位置的知识点。</p>
        </div>
        {overview.capabilities.length > 0 ? (
          <div className="portfolio-capability-list">
            {overview.capabilities.map((capability) => (
              <article key={capability.name}>
                <div className="portfolio-capability-title">
                  <h3>{capability.name}</h3>
                  <span className={capability.status}>{statusLabels[capability.status]}</span>
                </div>
                <p>应用项目：{capability.projects.map((project) => <Link key={project.id} to={`/portfolio-projects/${project.id}/showcase`}>{project.title}</Link>)}</p>
                <div className="portfolio-capability-files">{capability.evidence_locations.slice(0, 6).map((file) => <code key={file}>{file}</code>)}</div>
              </article>
            ))}
          </div>
        ) : <div className="portfolio-overview-empty">回传项目的 Codex 分析后，这里会出现带真实代码位置的能力。</div>}
      </section>

      {overview.technologies.length > 0 && (
        <section className="card portfolio-overview-section">
          <div className="portfolio-overview-heading">
            <div><small>TECHNOLOGY USAGE</small><h2>项目中使用的技术</h2></div>
            <p>这些名称来自项目技术栈，用于说明使用范围，不单独代表精通程度。</p>
          </div>
          <div className="portfolio-technology-cloud">{overview.technologies.map((item) => <span key={item.name}>{item.name}<small>{item.project_count} 个项目</small></span>)}</div>
        </section>
      )}

      <section className="portfolio-overview-section">
        <div className="portfolio-overview-heading">
          <div><small>REPRESENTATIVE WORK</small><h2>代表项目与简历要点</h2></div>
          <p>简历描述只为已经完成真实代码分析的项目生成。</p>
        </div>
        <div className="portfolio-overview-projects">
          {overview.projects.map((project) => (
            <article className="card" key={project.id}>
              <div className="portfolio-overview-project-meta">
                <span className={project.overall_status}>{statusLabels[project.overall_status]}</span>
                <strong>{project.completion_percent}%</strong>
              </div>
              <h3>{project.title}</h3>
              <p>{project.headline || project.objective}</p>
              {project.analysis_available ? (
                <ul>{project.resume_bullets.map((bullet, index) => <li key={`${bullet}-${index}`}>{bullet}</li>)}</ul>
              ) : <div className="portfolio-project-awaiting">等待 Codex 真实代码分析后生成简历要点。</div>}
              <div className="portfolio-project-proof">
                <span>{project.verified_feature_count} 个核心功能</span>
                <span>{project.knowledge_count} 个知识映射</span>
                <span>{project.passed_check_count} 项通过检查</span>
              </div>
              <div className="portfolio-overview-project-links">
                <Link to={`/portfolio-projects/${project.id}`}>项目工作台</Link>
                {project.analysis_available && <Link to={`/portfolio-projects/${project.id}/showcase`}>面试展示页</Link>}
                {project.github_url && <a href={project.github_url} target="_blank" rel="noreferrer">GitHub</a>}
                {project.demo_url && <a href={project.demo_url} target="_blank" rel="noreferrer">在线演示</a>}
              </div>
            </article>
          ))}
        </div>
      </section>

      {overview.interview_order.length > 0 && (
        <section className="card portfolio-overview-section">
          <div className="portfolio-overview-heading"><div><small>INTERVIEW FLOW</small><h2>推荐面试展示顺序</h2></div></div>
          <ol className="portfolio-interview-order">{overview.interview_order.map((project) => <li key={project.id}><strong>{project.title}</strong><p>{project.reason}</p><Link to={`/portfolio-projects/${project.id}/showcase`}>打开面试展示页 →</Link></li>)}</ol>
        </section>
      )}

      <section className="card portfolio-overview-section portfolio-markdown-section">
        <div className="portfolio-overview-heading">
          <div><small>READY TO USE</small><h2>可复制作品集 Markdown</h2></div>
          <button className="btn btn-secondary btn-sm" onClick={copyMarkdown}>{copied ? "已复制" : "复制全文"}</button>
        </div>
        <pre>{overview.markdown_content}</pre>
      </section>
    </div>
  );
}
