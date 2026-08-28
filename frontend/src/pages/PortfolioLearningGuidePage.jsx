import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Breadcrumb from "../components/Breadcrumb";
import { portfolioAPI } from "../services/api";
import "./PortfolioCodeAnalysisPage.css";
import "./PortfolioLearningGuidePage.css";


function ConceptLadder({ items }) {
  return (
    <section className="concept-ladder" id="concept-ladder">
      <header>
        <small>先建立直觉，再记专业名称</small>
        <h3>第一次接触，只需要按顺序认识这些东西</h3>
        <p>每次只增加一个概念。先读日常语言，理解以后再看蓝色的专业名称。</p>
      </header>
      <ol>
        {items.map((item, index) => (
          <li key={`${item.term}-${index}`}>
            <span className="concept-step">{index + 1}</span>
            <article>
              <p className="concept-before-term">{item.before_term}</p>
              <div className="concept-name"><small>它的专业名称是</small><strong>{item.term}</strong></div>
              <p>{item.plain_explanation}</p>
              <blockquote>可以把它想成：{item.analogy}</blockquote>
              <p><b>放到这个作品里举个例子：</b>{item.project_role}</p>
              <p className="concept-remember">这一小步只要记住：{item.remember}</p>
            </article>
          </li>
        ))}
      </ol>
    </section>
  );
}


function LearningFlow({ items }) {
  return (
    <section className="beginner-learning-flow" id="learning-flow">
      <header><small>先看整条流水线</small><h3>如果把作品实现出来，它会怎样运转</h3><p>这里讲逻辑，不代表当前已经生成了源码。</p></header>
      <ol>{items.map((item, index) => (
        <li key={`${item.label}-${index}`}>
          <span>{index + 1}</span><h4>{item.label}</h4>
          <p>你会看到：{item.what_user_sees}</p>
          <p>程序会做：{item.what_program_would_do}</p>
          <small>为什么需要：{item.why_needed}</small>
          <div className="flow-terms">以后会看到：{item.technical_terms.map((term) => <code key={term}>{term}</code>)}</div>
        </li>
      ))}</ol>
    </section>
  );
}


function StorySections({ items }) {
  return (
    <section className="beginner-story-sections" id="story-sections">
      <header><small>现在才逐步增加细节</small><h3>每一节只弄懂一件事</h3><p>公开项目的数字会直接放在相关讲解中，并明确标记来源身份。</p></header>
      {items.map((item, index) => (
        <article key={`${item.title}-${index}`}>
          <div className="story-section-heading"><span>{String(index + 1).padStart(2, "0")}</span><div><small>这一节学会：{item.learning_goal}</small><h4>{item.title}</h4></div></div>
          <div className="story-section-content">
            {item.content.split(/\n+/).filter(Boolean).map((paragraph, paragraphIndex) => <p key={paragraphIndex}>{paragraph}</p>)}
            <div className="new-terms">这一节新认识：{item.new_terms.map((term) => <span key={term}>{term}</span>)}</div>
            <div className="section-checkpoint">先别急着继续：{item.checkpoint}</div>
          </div>
        </article>
      ))}
    </section>
  );
}


function ReferenceResults({ results, sources, status }) {
  const sourceByUrl = new Map(sources.map((source) => [source.source_url, source]));
  return (
    <section className="planning-reference-section" id="reference-results">
      <header><small>数字从哪里来</small><h3>正文使用的外部参考结果</h3></header>
      <p className="reference-boundary">这些数据帮助理解作品可能出现的训练现象，不是当前作品的实际成绩，也不能作为当前作品已经完成的证据。</p>
      {results.length > 0 ? <div className="reference-result-list">{results.map((item, index) => {
        const source = sourceByUrl.get(item.source_url);
        return <article key={`${item.source_url}-${index}`}>
          <h4>{item.claim}</h4><p>{item.source_context}</p><p><b>与当前规划的差异：</b>{item.differences}</p>
          <a href={item.source_url} target="_blank" rel="noreferrer">查看来源：{item.source_name} →</a>
          {source && <small>GitHub ★ {source.stars} · 许可证：{source.license}</small>}
          <strong>{item.disclaimer}</strong>
        </article>;
      })}</div> : <div className="reference-empty">{status === "search_failed" ? "本次网络检索失败，因此指南没有填入未经核实的数字。" : "没有找到包含可核实训练数字的高度相似公开项目，指南没有编造结果。"}</div>}
    </section>
  );
}


export default function PortfolioLearningGuidePage() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [guide, setGuide] = useState(null);
  const [loading, setLoading] = useState(true);
  const [markingLearned, setMarkingLearned] = useState(false);
  const [learningNotice, setLearningNotice] = useState("");
  const [learningError, setLearningError] = useState("");
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      setError(null);
      const [projectData, guideData] = await Promise.all([
        portfolioAPI.getProject(Number(id)),
        portfolioAPI.getConceptGuide(Number(id)),
      ]);
      setProject(projectData);
      setGuide(guideData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  const completeLearning = async () => {
    try {
      setMarkingLearned(true);
      setLearningNotice("");
      setLearningError("");
      const result = await portfolioAPI.completeLearning(Number(id));
      setProject((current) => ({
        ...current,
        learning_count: result.learning_count,
      }));
      setLearningNotice(`已记录第 ${result.learning_count} 次学习。`);
    } catch (err) {
      setLearningError(err.message);
    } finally {
      setMarkingLearned(false);
    }
  };

  if (loading) return <div className="loading">正在加载作品学习指南...</div>;
  if (!project) return <div className="error">作品项目不存在</div>;
  const content = guide?.content;
  const learningCount = project.learning_count || 0;

  return <main className="page beginner-guide-page planning-guide-page">
    <Breadcrumb items={[{ label: "我的作品", to: "/portfolio-projects" }, { label: project.title, to: `/portfolio-projects/${project.id}` }, { label: "作品学习指南" }]} />
    <header className="beginner-guide-hero planning-guide-hero">
      <small>LEARN BEFORE BUILDING</small><h1>{content?.guide_title || "先理解作品，再决定是否学习源码"}</h1>
      <p>默认只帮你把作品讲明白，不要求先编程、训练或生成源码。学习内容由 Codex 根据作品资料生成，不会在网页内调用 DeepSeek。</p>
    </header>
    {error && <div className="beginner-guide-error">{error}</div>}
    {!guide ? <section className="card guide-empty"><h2>还没有作品学习指南</h2><p>请在 Codex 对话中发送“为这个作品生成学习指南”。我会根据课程、项目资料和你的零基础学习目标生成后导入这里。</p></section> : <>
      <nav className="guide-section-nav"><a href="#plain-story">先听懂故事</a><a href="#concept-ladder">认识概念</a><a href="#learning-flow">理解流程</a><a href="#story-sections">逐节学习</a><a href="#reference-results">核对来源</a><a href="#source-learning">源码学习（可选）</a></nav>
      <section className="plain-project-story" id="plain-story"><span>第一部分 · 先不看代码</span><h2>{content.beginner_story.title}</h2><p className="story-reading-goal">{content.beginner_story.after_reading}</p><div className="continuous-story">{content.beginner_story.content.split(/\n+/).filter(Boolean).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>
        <ConceptLadder items={content.concept_ladder} /><LearningFlow items={content.learning_flow} /><StorySections items={content.story_sections} />
        <section className="beginner-self-checks"><header><small>不用背定义</small><h3>用自己的话检查是否真的懂了</h3></header>{content.self_checks.map((item, index) => <details key={`${item.question}-${index}`}><summary>{index + 1}. {item.question}</summary><p className="self-check-hint">提示：{item.hint}</p><p>{item.answer}</p><small>{item.why_it_matters}</small></details>)}</section>
      </section>
      <ReferenceResults results={content.reference_results} sources={guide.reference_sources} status={guide.reference_status} />
      <section className="planning-outcomes"><article><h3>如果以后真正实现，可以展示什么</h3><ul>{content.expected_outcomes.map((item) => <li key={item}>{item}</li>)}</ul></article><article><h3>现在必须知道的边界</h3><ul>{content.limitations.map((item) => <li key={item}>{item}</li>)}</ul></article></section>
      <section className="guide-learning-completion">
        <div>
          <small>LEARNING CHECK-IN</small>
          <h2>{learningCount > 0 ? `你已经学习过 ${learningCount} 次` : "学完后记录这次学习"}</h2>
          <p>每完整学习一次就点击一次，次数会永久保存，并显示在章节作品卡片上。</p>
          <p className="guide-learning-feedback" aria-live="polite">
            {learningError || learningNotice}
          </p>
        </div>
        <button className="btn btn-primary" onClick={completeLearning} disabled={markingLearned}>
          {markingLearned ? "正在记录..." : "我已学完一次"}
        </button>
      </section>
      <section className="optional-source-learning" id="source-learning"><small>OPTIONAL NEXT STEP</small><h2>{content.source_learning.title}</h2><p>{content.source_learning.description}</p><div><article><h3>开发当前作品</h3><p>{content.source_learning.develop_option}</p><Link className="btn btn-primary" to={`/portfolio-projects/${project.id}/execution`}>进入 Codex 开发流程</Link></article><article><h3>学习相似开源项目</h3><p>{content.source_learning.reference_option}</p><Link className="btn btn-secondary" to={`/portfolio-projects/${project.id}/code-analysis`}>进入源码讲解入口</Link></article></div></section>
      <footer className="guide-source-note">本指南基于课程内容和公开参考资料生成；外部结果不代表当前作品已经完成。</footer>
    </>}
  </main>;
}
