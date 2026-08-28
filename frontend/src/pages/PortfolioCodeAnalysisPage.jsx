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

function sourceLines(source = "") {
  const lines = source.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  if (lines.length > 1 && lines.at(-1) === "") lines.pop();
  return lines;
}

function CodeLines({ source, startLine = 1, endLine }) {
  const lines = sourceLines(source);
  const finalLine = endLine || lines.length;
  return (
    <pre className="annotated-source-code"><code>{lines.slice(startLine - 1, finalLine).map((line, index) => (
      <span className="annotated-code-line" key={`${startLine + index}-${line}`}>
        <span className="annotated-line-number">{startLine + index}</span>
        <span className="annotated-line-text">{line || " "}</span>
      </span>
    ))}</code></pre>
  );
}

function AnnotationNote({ annotation }) {
  return (
    <aside className="source-annotation-note">
      <small>第 {annotation.start_line}-{annotation.end_line} 行</small>
      <h4>{annotation.title}</h4>
      <p>{annotation.plain_explanation}</p>
      <dl>
        <div><dt>为什么需要</dt><dd>{annotation.why_needed}</dd></div>
        <div><dt>输入和输出</dt><dd>{annotation.input_output}</dd></div>
        <div><dt>前后怎样连起来</dt><dd>{annotation.connection}</dd></div>
        <div><dt>课程知识</dt><dd>{annotation.course_knowledge}</dd></div>
        <div className="annotation-warning"><dt>初学者注意</dt><dd>{annotation.beginner_warning}</dd></div>
      </dl>
    </aside>
  );
}

function ModernLearningGuide({ guide, analysis, projectId }) {
  const readingPaths = guide.code_map.reading_order.map((item) => item.path);
  const orderedFiles = [
    ...readingPaths.map((path) => guide.annotated_files.find((file) => file.path === path)).filter(Boolean),
    ...guide.annotated_files.filter((file) => !readingPaths.includes(file.path)),
  ];
  const [selectedPath, setSelectedPath] = useState(guide.code_map.entry_point || orderedFiles[0]?.path);
  const [showAnnotations, setShowAnnotations] = useState(true);
  const selectedFile = orderedFiles.find((file) => file.path === selectedPath) || orderedFiles[0];
  const storyParagraphs = guide.beginner_story.content.split(/\n{2,}/).filter(Boolean);
  const supportingFiles = guide.source_inventory.filter((item) => item.category !== "annotated_source");
  const hasBeginnerPath = Boolean(
    guide.concept_ladder?.length
    && guide.learning_flow?.length
    && guide.story_sections?.length
    && guide.self_checks?.length
  );

  useEffect(() => {
    if (!orderedFiles.some((file) => file.path === selectedPath)) {
      setSelectedPath(guide.code_map.entry_point || orderedFiles[0]?.path);
    }
  }, [guide, orderedFiles, selectedPath]);

  return (
    <>
      <nav className="guide-section-nav modern-guide-nav">
        <a href="#plain-story">先知道要做什么</a>
        {hasBeginnerPath && <a href="#concept-ladder">从生活经验认识概念</a>}
        {hasBeginnerPath && <a href="#learning-flow">走一遍完整流程</a>}
        {hasBeginnerPath && <a href="#story-sections">一小步一小步学</a>}
        <a href="#code-map">再看代码地图</a>
        <a href="#annotated-source">最后读完整源码</a>
      </nav>

      <section className="plain-project-story" id="plain-story">
        <span>第一部分 · 先不看代码</span>
        <h2>{guide.beginner_story.title}</h2>
        <p className="story-reading-goal">{guide.beginner_story.after_reading}</p>
        <div className="continuous-story">{storyParagraphs.map((paragraph, index) => <p key={`${paragraph.slice(0, 20)}-${index}`}>{paragraph}</p>)}</div>

        {hasBeginnerPath && <>
          <section className="concept-ladder" id="concept-ladder">
            <header><small>先建立直觉，再记专业名称</small><h3>第一次接触，只需要按顺序认识这些东西</h3><p>每次只增加一个新概念。先读日常语言，理解以后再看蓝色的专业名称。</p></header>
            <ol>
              {guide.concept_ladder.map((item, index) => <li key={`${item.term}-${index}`}>
                <span className="concept-step">{index + 1}</span>
                <article>
                  <p className="concept-before-term">{item.before_term}</p>
                  <div className="concept-name"><small>它的专业名称是</small><strong>{item.term}</strong></div>
                  <p>{item.plain_explanation}</p>
                  <blockquote><b>可以把它想成：</b>{item.analogy}</blockquote>
                  <p><b>在这个项目里：</b>{item.project_role}</p>
                  <p className="concept-remember">这一小步只要记住：{item.remember}</p>
                </article>
              </li>)}
            </ol>
          </section>

          <section className="beginner-learning-flow" id="learning-flow">
            <header><small>先看整条流水线</small><h3>一张图片是怎样一步步变成答案的</h3><p>暂时不用理解代码，只看事情发生的顺序。</p></header>
            <ol>
              {guide.learning_flow.map((item, index) => <li key={`${item.label}-${index}`}>
                <span>{index + 1}</span>
                <div><h4>{item.label}</h4><p><b>你看到：</b>{item.what_user_sees}</p><p><b>程序在做：</b>{item.what_program_does}</p><small>为什么需要：{item.why_needed}</small>{item.technical_terms.length > 0 && <div className="flow-terms">以后会看到这些名字：{item.technical_terms.map((term) => <code key={term}>{term}</code>)}</div>}</div>
              </li>)}
            </ol>
          </section>

          <section className="beginner-story-sections" id="story-sections">
            <header><small>现在才逐步增加细节</small><h3>每一节只弄懂一件事</h3><p>不需要一次记住全部内容。能回答每节末尾的问题，就可以继续。</p></header>
            {guide.story_sections.map((section, index) => <article key={`${section.title}-${index}`}>
              <div className="story-section-heading"><span>{String(index + 1).padStart(2, "0")}</span><div><small>这一节学会：{section.learning_goal}</small><h4>{section.title}</h4></div></div>
              <div className="story-section-content">{section.content.split(/\n{2,}/).filter(Boolean).map((paragraph, paragraphIndex) => <p key={`${paragraph.slice(0, 20)}-${paragraphIndex}`}>{paragraph}</p>)}</div>
              {section.new_terms.length > 0 && <div className="new-terms"><b>这一节新认识：</b>{section.new_terms.map((term) => <span key={term}>{term}</span>)}</div>}
              <CodeLocations locations={section.code_locations} />
              <div className="section-checkpoint"><b>先别急着继续：</b>{section.checkpoint}</div>
            </article>)}
          </section>

          <section className="beginner-self-checks">
            <header><small>不用背定义</small><h3>用自己的话检查是否真的懂了</h3></header>
            {guide.self_checks.map((item, index) => <details key={`${item.question}-${index}`}><summary>{index + 1}. {item.question}</summary><p className="self-check-hint">提示：{item.hint}</p><p><b>答案：</b>{item.answer}</p><small>理解它的意义：{item.why_it_matters}</small></details>)}
          </section>
        </>}

        <div className="quick-verification">
          <div><strong>听懂后马上验证</strong><p>{guide.beginner_story.quick_verification.action}</p></div>
          <code>{guide.beginner_story.quick_verification.command}</code>
          <p><b>预计看到：</b>{guide.beginner_story.quick_verification.expected_result}</p>
          <small>这一步证明：{guide.beginner_story.quick_verification.what_it_proves}</small>
        </div>
      </section>

      <section className="modern-code-map" id="code-map">
        <header><span>第二部分</span><h2>先看清全貌，再进入文件</h2><p>{guide.code_map.overview}</p></header>
        <div className="runtime-flow">
          {guide.code_map.runtime_flow.map((step, index) => <div key={`${step}-${index}`}><span>{index + 1}</span><p>{step}</p></div>)}
        </div>
        <h3>推荐阅读顺序</h3>
        <ol className="reading-order">
          {guide.code_map.reading_order.map((item) => <li key={item.path}>
            <button type="button" onClick={() => setSelectedPath(item.path)}><code>{item.path}</code><strong>{item.role}</strong><span>{item.why_read_now}</span></button>
          </li>)}
        </ol>
        <details className="source-inventory"><summary>查看完整项目文件清单</summary><ul>{guide.source_inventory.map((item) => <li key={item.path} data-category={item.category}><code>{item.path}</code><span>{item.reason}</span></li>)}</ul></details>
      </section>

      <section className="annotated-source-section" id="annotated-source">
        <header><span>第三部分</span><h2>在完整源码旁边，像老师一样逐段批注</h2><p>代码原文没有被改写。你可以跟着批注学，也可以切换到干净源码。</p></header>
        <div className="source-reader">
          <aside className="source-file-list">
            <strong>全部人工源码</strong>
            {orderedFiles.map((file, index) => <button className={file.path === selectedFile?.path ? "active" : ""} type="button" key={file.path} onClick={() => setSelectedPath(file.path)}><span>{index + 1}</span><code>{file.path}</code></button>)}
            {supportingFiles.length > 0 && <small>{supportingFiles.length} 个辅助或排除文件已在上方清单说明。</small>}
          </aside>
          {selectedFile && <div className="source-file-viewer">
            <div className="source-viewer-toolbar"><div><code>{selectedFile.path}</code><span>{selectedFile.role} · {selectedFile.language}</span></div><div><button className={showAnnotations ? "active" : ""} type="button" onClick={() => setShowAnnotations(true)}>跟着老师学</button><button className={!showAnnotations ? "active" : ""} type="button" onClick={() => setShowAnnotations(false)}>查看干净源码</button></div></div>
            {showAnnotations ? <div className="annotated-code-blocks">{selectedFile.annotations.map((annotation) => <article key={`${annotation.start_line}-${annotation.end_line}`}><CodeLines source={selectedFile.source} startLine={annotation.start_line} endLine={annotation.end_line} /><AnnotationNote annotation={annotation} /></article>)}</div> : <CodeLines source={selectedFile.source} />}
          </div>}
        </div>
      </section>

      <footer className="guide-source-note">本指南由 Codex 基于真实项目工作区生成 · 源码指纹 {analysis.source_fingerprint.slice(0, 12)}… · 专业技术证据请查看<Link to={`/portfolio-projects/${projectId}/showcase`}>面试展示页</Link></footer>
    </>
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
    if (file.size > 12 * 1024 * 1024) {
      setError("Codex 分析 JSON 不能超过 12 MB");
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
  const hasAnnotatedSource = Boolean(guide?.beginner_story && guide?.code_map && guide?.annotated_files?.length);

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

      {hasAnnotatedSource && <ModernLearningGuide guide={guide} analysis={analysis} projectId={project.id} />}

      {guide && !hasAnnotatedSource && (
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
