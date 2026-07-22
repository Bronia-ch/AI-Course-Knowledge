import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { portfolioAPI } from "../services/api";
import "./PortfolioShowcasePage.css";

const unique = (items) => [...new Set(items.filter(Boolean))];

function EvidenceFiles({ files = [] }) {
  if (!files.length) return null;
  return <div className="showcase-file-list">{files.map((file) => <code key={file}>{file}</code>)}</div>;
}

export default function PortfolioShowcasePage() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([portfolioAPI.getProject(Number(id)), portfolioAPI.getCodeAnalysis(Number(id))])
      .then(([projectData, analysisData]) => {
        setProject(projectData);
        setAnalysis(analysisData);
      })
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) return <div className="error">加载失败: {error}</div>;
  if (!project) return <div className="loading">加载面试展示页...</div>;

  const showcase = analysis?.interview_showcase || {};
  const verifiedFeatures = showcase.verified_features || [];
  const highlights = showcase.highlights || [];
  const challenges = showcase.technical_challenges || [];
  const verification = analysis?.verification_evidence || [];
  const passedChecks = verification.filter((item) => item.status === "passed");
  const knowledgeMapping = analysis?.knowledge_mapping || [];
  const coveredKnowledge = knowledgeMapping.length || project.knowledge_points.length;
  const publicationLinks = [
    project.showcase.github_url,
    project.showcase.demo_url,
    project.showcase.demo_video_url,
  ].filter(Boolean);
  const screenshots = project.showcase.screenshot_urls || [];
  const technologyTags = unique([...project.technology_stack, ...project.knowledge_points]);

  return (
    <main className="portfolio-showcase-page">
      <nav>
        <Link to={`/portfolio-projects/${project.id}`}>← 返回项目工作台</Link>
        <span>{analysis ? "内容来自 Codex 真实工作区分析" : "等待 Codex 真实代码分析"}</span>
      </nav>

      <header className="portfolio-showcase-hero">
        <small>PORTFOLIO PROJECT</small>
        <h1>{project.title}</h1>
        <p>{showcase.headline || project.objective}</p>
        {publicationLinks.length > 0 && (
          <div className="portfolio-showcase-links">
            {project.showcase.github_url && <a href={project.showcase.github_url} target="_blank" rel="noreferrer">查看源代码</a>}
            {project.showcase.demo_url && <a href={project.showcase.demo_url} target="_blank" rel="noreferrer">打开在线演示</a>}
            {project.showcase.demo_video_url && <a href={project.showcase.demo_video_url} target="_blank" rel="noreferrer">观看演示视频</a>}
          </div>
        )}
      </header>

      <section className="portfolio-showcase-summary">
        <article><strong>{verifiedFeatures.length}</strong><span>已验证核心功能</span></article>
        <article><strong>{coveredKnowledge}</strong><span>覆盖课程知识点</span></article>
        <article><strong>{passedChecks.length}</strong><span>通过的构建与测试</span></article>
      </section>

      <section className="portfolio-showcase-grid">
        <article>
          <h2>项目解决什么问题</h2>
          <p>{project.use_case}</p>
        </article>
        <article>
          <h2>真实系统架构</h2>
          <p>{analysis?.actual_architecture || project.architecture}</p>
        </article>
      </section>

      <section className="portfolio-showcase-block">
        <h2>技术栈与课程知识</h2>
        <div className="portfolio-showcase-tags">
          {technologyTags.map((item) => <span key={item}>{item}</span>)}
        </div>
      </section>

      {analysis ? (
        <>
          {verifiedFeatures.length > 0 && (
            <section className="portfolio-showcase-block">
              <div className="showcase-section-heading"><small>WHAT I BUILT</small><h2>已验证核心功能</h2></div>
              <div className="showcase-feature-grid">
                {verifiedFeatures.map((item, index) => (
                  <article key={`${item.name}-${index}`}>
                    <h3>{item.name}</h3>
                    <p>{item.proof}</p>
                    <EvidenceFiles files={item.evidence_files} />
                  </article>
                ))}
              </div>
            </section>
          )}

          {(highlights.length > 0 || challenges.length > 0) && (
            <section className="portfolio-showcase-grid">
              {highlights.length > 0 && (
                <article>
                  <h2>项目亮点</h2>
                  <div className="showcase-story-list">{highlights.map((item, index) => <div key={`${item.title}-${index}`}><h3>{item.title}</h3><p>{item.value}</p><EvidenceFiles files={item.evidence_files} /></div>)}</div>
                </article>
              )}
              {challenges.length > 0 && (
                <article>
                  <h2>技术难点与解决方案</h2>
                  <div className="showcase-story-list">{challenges.map((item, index) => <div key={`${item.challenge}-${index}`}><h3>{item.challenge}</h3><p>{item.solution}</p><EvidenceFiles files={item.evidence_files} /></div>)}</div>
                </article>
              )}
            </section>
          )}

          {analysis.key_modules.length > 0 && (
            <section className="portfolio-showcase-block">
              <h2>核心模块与代码依据</h2>
              <div className="professional-modules">{analysis.key_modules.map((item, index) => <article key={`${item.path}-${index}`}><code>{item.path}</code><h3>{item.responsibility}</h3><p>{item.evidence}</p></article>)}</div>
            </section>
          )}

          {verification.length > 0 && (
            <section className="portfolio-showcase-block">
              <h2>构建与测试记录</h2>
              <div className="professional-verification">{verification.map((item, index) => <article key={`${item.command}-${index}`}><code>{item.command || "未运行命令"}</code><strong className={item.status}>{item.status}</strong><p>{item.summary}</p></article>)}</div>
            </section>
          )}

          {(showcase.pitch_30s || showcase.pitch_2min) && (
            <section className="portfolio-showcase-grid showcase-pitches">
              {showcase.pitch_30s && <article><small>30 SECONDS</small><h2>快速自我介绍</h2><p>{showcase.pitch_30s}</p></article>}
              {showcase.pitch_2min && <article><small>2 MINUTES</small><h2>完整项目讲述</h2><p className="professional-preserve-lines">{showcase.pitch_2min}</p></article>}
            </section>
          )}

          {(analysis.interview_demo.length > 0 || analysis.risks_and_limitations.length > 0) && (
            <section className="portfolio-showcase-grid">
              {analysis.interview_demo.length > 0 && <article><h2>面试演示顺序</h2><ol>{analysis.interview_demo.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ol></article>}
              {analysis.risks_and_limitations.length > 0 && <article><h2>风险、限制和未验证内容</h2><ul>{analysis.risks_and_limitations.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></article>}
            </section>
          )}

          {analysis.interview_questions.length > 0 && (
            <section className="portfolio-showcase-block">
              <h2>面试官可能追问</h2>
              <div className="professional-questions">{analysis.interview_questions.map((item, index) => <details key={`${item.question}-${index}`}><summary>{item.question}</summary><ul>{item.answer_points.map((point, pointIndex) => <li key={`${point}-${pointIndex}`}>{point}</li>)}</ul></details>)}</div>
            </section>
          )}
        </>
      ) : (
        <section className="portfolio-showcase-block professional-analysis-empty">
          <h2>面试展示内容将在 Codex 分析后自动生成</h2>
          <p>项目验收完成后，让 Codex 生成 portfolio_analysis_result.json 并回传。页面会自动整理已验证功能、亮点、难点、测试记录和面试讲述稿。</p>
          <Link to={`/portfolio-projects/${project.id}/code-analysis`}>前往回传 JSON →</Link>
        </section>
      )}

      {screenshots.length > 0 && (
        <section className="portfolio-showcase-block">
          <h2>项目截图</h2>
          <div className="showcase-screenshots">{screenshots.map((url) => <a href={url} target="_blank" rel="noreferrer" key={url}><img src={url} alt="项目界面截图" /></a>)}</div>
        </section>
      )}
    </main>
  );
}
