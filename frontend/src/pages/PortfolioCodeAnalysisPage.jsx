import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { portfolioAPI } from "../services/api";
import "./PortfolioCodeAnalysisPage.css";

function CodeLocations({ locations = [] }) {
  if (locations.length === 0) return null;
  return (
    <details className="learning-code-locations">
      <summary>查看对应的真实代码</summary>
      <div>{locations.map((location) => <code key={location}>{location}</code>)}</div>
    </details>
  );
}

export default function PortfolioCodeAnalysisPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const [project, setProject] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [resultText, setResultText] = useState("");
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([portfolioAPI.getProject(projectId), portfolioAPI.getCodeAnalysis(projectId)])
      .then(([projectData, analysisData]) => {
        setProject(projectData);
        setAnalysis(analysisData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  const readResultFile = async (file) => {
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setError("Codex 分析 JSON 不能超过 2 MB");
      return;
    }
    setResultText(await file.text());
    setError(null);
  };

  const importResult = async (event) => {
    event.preventDefault();
    try {
      setImporting(true);
      setError(null);
      const data = await portfolioAPI.importCodexAnalysis(projectId, JSON.parse(resultText));
      setAnalysis(data);
    } catch (err) {
      setError(err instanceof SyntaxError ? "JSON 格式无效，请检查 Codex 输出文件" : err.message);
    } finally {
      setImporting(false);
    }
  };

  if (loading) return <div className="loading">加载项目学习指南...</div>;
  if (!project) return <div className="error">{error || "作品项目不存在"}</div>;

  const guide = analysis?.learning_guide;

  return (
    <main className="page beginner-guide-page">
      <nav className="beginner-guide-breadcrumb">
        <Link to="/portfolio-projects">我的作品</Link><span>/</span>
        <Link to={`/portfolio-projects/${project.id}`}>{project.title}</Link><span>/ 项目学习指南</span>
      </nav>

      <header className="beginner-guide-hero">
        <small>LEARN THE PROJECT</small>
        <h1>从零读懂这个项目</h1>
        <p>这里不是写给工程师看的审计报告，而是一条带你从“它有什么用”走到“我能自己讲明白”的学习路线。</p>
        <div><Link to={`/portfolio-projects/${project.id}/showcase`}>前往面试展示页 →</Link></div>
      </header>

      {error && <div className="beginner-guide-error">{error}</div>}

      <details className="card guide-import-panel" open={!analysis}>
        <summary>{analysis ? "更新 Codex 生成的学习指南" : "上传 Codex 生成的学习指南"}</summary>
        <form onSubmit={importResult}>
          <p>选择项目根目录中的 portfolio_analysis_result.json，或者粘贴文件内容。无需上传源码 ZIP。</p>
          <input type="file" accept=".json,application/json" onChange={(event) => readResultFile(event.target.files[0])} />
          <textarea rows={7} value={resultText} onChange={(event) => setResultText(event.target.value)} placeholder="粘贴 portfolio_analysis_result.json 内容..." />
          <button className="btn btn-success" disabled={!resultText.trim() || importing} type="submit">{importing ? "正在验证..." : "导入并生成学习路线"}</button>
        </form>
      </details>

      {!analysis && <section className="card guide-empty"><h2>还没有项目学习指南</h2><p>让 Codex 完成项目分析并生成 JSON，上传后这里会按照初学者的学习顺序讲解整个项目。</p></section>}

      {analysis && !guide && (
        <section className="card guide-legacy">
          <h2>这是一份旧版技术分析</h2>
          <p>旧结果中还没有面向初学者的连续教程。请使用新版执行包中的 CODEX_ANALYSIS_REQUEST.md 重新生成 JSON。</p>
          <strong>旧版项目摘要</strong><p>{analysis.implementation_summary}</p>
        </section>
      )}

      {guide && (
        <>
          <nav className="guide-section-nav">
            <a href="#overview">先看全貌</a><a href="#terms">必要概念</a><a href="#story">运行故事</a><a href="#chapters">跟着代码学</a><a href="#practice">亲手验证</a><a href="#summary">学习总结</a>
          </nav>

          <section className="guide-overview" id="overview">
            <span>第一步 · 先看全貌</span>
            <h2>{guide.project_overview.one_sentence}</h2>
            <div className="guide-overview-story"><article><small>它解决的问题</small><p>{guide.project_overview.problem_story}</p></article><article><small>最后做出了什么</small><p>{guide.project_overview.final_result}</p></article><article><small>你要学会什么</small><p>{guide.project_overview.learner_goal}</p></article></div>
          </section>

          <section className="guide-section" id="terms">
            <header><span>第二步</span><h2>开始前，先认识这些词</h2><p>不要求背定义，只要先建立直觉。</p></header>
            <div className="guide-terms">{guide.prerequisites.map((item, index) => <article key={`${item.term}-${index}`}><h3>{item.term}</h3><p>{item.plain_explanation}</p><div><b>可以把它想成：</b>{item.analogy}</div><div><b>在这个项目里：</b>{item.project_example}</div><small>现在可以先忽略：{item.can_ignore_for_now}</small></article>)}</div>
          </section>

          <section className="guide-section" id="story">
            <header><span>第三步</span><h2>像讲故事一样走完一次运行过程</h2><p>先理解事情发生的顺序，再去看代码。</p></header>
            <ol className="guide-story">{guide.running_story.map((item, index) => <li key={`${item.step}-${index}`}><span>{index + 1}</span><article><h3>{item.step}</h3><p><b>你做了什么：</b>{item.user_action}</p><p><b>系统做了什么：</b>{item.system_action}</p><div>{item.plain_explanation}</div><CodeLocations locations={item.code_locations} /></article></li>)}</ol>
          </section>

          <section className="guide-section" id="chapters">
            <header><span>第四步</span><h2>现在跟着代码，一章一章学</h2><p>每章只解决一个问题，读完再进入下一章。</p></header>
            <div className="guide-learning-chapters">{guide.chapters.map((chapter, index) => <article key={`${chapter.title}-${index}`}><div className="guide-chapter-number">{String(index + 1).padStart(2, "0")}</div><div><small>本章目标：{chapter.learning_goal}</small><h3>{chapter.title}</h3><p>{chapter.plain_explanation}</p><blockquote><b>为什么需要它：</b>{chapter.why_it_matters}</blockquote><p className="guide-analogy"><b>生活类比：</b>{chapter.analogy}</p><h4>看代码时重点关注</h4><ul>{chapter.focus_points.map((point, pointIndex) => <li key={`${point}-${pointIndex}`}>{point}</li>)}</ul><CodeLocations locations={chapter.code_locations} /><strong className="guide-takeaway">学完记住：{chapter.takeaway}</strong></div></article>)}</div>
          </section>

          <section className="guide-section">
            <header><span>第五步</span><h2>课程知识是怎样变成代码的</h2><p>把抽象知识和真实项目连接起来。</p></header>
            <div className="guide-knowledge-lessons">{guide.knowledge_lessons.map((item, index) => <article key={`${item.knowledge_point}-${index}`}><h3>{item.knowledge_point}</h3><p><b>它是什么：</b>{item.what_it_is}</p><p><b>为什么需要：</b>{item.why_needed}</p><p><b>如果不用：</b>{item.without_it}</p><p><b>项目里怎么用：</b>{item.project_usage}</p><div className="guide-try">你可以这样验证：{item.try_it_yourself}</div><CodeLocations locations={item.code_locations} /></article>)}</div>
          </section>

          <section className="guide-section" id="practice">
            <header><span>第六步</span><h2>亲手运行和验证一次</h2><p>看到真实结果，理解才会变成自己的。</p></header>
            <div className="guide-hands-on">{guide.hands_on.map((item, index) => <article key={`${item.title}-${index}`}><span>{index + 1}</span><div><h3>{item.title}</h3><p>{item.action}</p>{item.command && <code>{item.command}</code>}<p><b>预计看到：</b>{item.expected_result}</p><small>这一步证明：{item.what_it_proves}</small></div></article>)}</div>
          </section>

          <section className="guide-section guide-two-columns">
            <div><header><span>第七步</span><h2>容易想错的地方</h2></header>{guide.common_misunderstandings.map((item, index) => <details key={`${item.question}-${index}`}><summary>{item.question}</summary><p>{item.plain_answer}</p></details>)}</div>
            <div><header><span>第八步</span><h2>用小练习确认理解</h2></header>{guide.exercises.map((item, index) => <article className="guide-exercise" key={`${item.title}-${index}`}><h3>{item.title}</h3><p>{item.task}</p><details><summary>需要提示时再打开</summary><p>{item.hint}</p></details><small>完成后你会理解：{item.expected_learning}</small></article>)}</div>
          </section>

          <section className="guide-summary" id="summary">
            <span>最后一步 · 把知识变成自己的</span><h2>学完后，你应该能讲清楚这些内容</h2>
            <div><article><h3>必须记住</h3><ul>{guide.summary.must_remember.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></article><article><h3>暂时可以忽略</h3><ul>{guide.summary.can_ignore_for_now.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></article></div>
            <blockquote>{guide.summary.teach_back_prompt}</blockquote>
            <h3>自测问题</h3><ol>{guide.summary.self_check_questions.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ol>
          </section>

          <footer className="guide-source-note">本指南由 Codex 基于真实项目工作区生成 · 源码指纹 {analysis.source_fingerprint.slice(0, 12)}… · 专业技术证据请查看<Link to={`/portfolio-projects/${project.id}/showcase`}>面试展示页</Link></footer>
        </>
      )}
    </main>
  );
}
