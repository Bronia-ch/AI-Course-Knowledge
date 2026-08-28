import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ExecutionPackageSection from "../components/ExecutionPackageSection";
import { portfolioAPI } from "../services/api";
import "./PortfolioExecutionPage.css";

const codexStartInstruction = "请先完整阅读 START_HERE.md 和 AGENTS.md，然后按照其中要求检查工作区、制定计划并分阶段完成项目。";
const codexReviewInstruction = "项目开发完成后，请完整阅读 CODE_REVIEW_PROMPT.md，基于当前工作区的真实代码执行全面审查，报告问题并完成必要的高优先级修复和验证。";
const codexExplanationInstruction = "代码审查和修复完成后，请完整阅读 PROJECT_EXPLANATION_PROMPT.md，基于最终真实代码向我讲解项目架构、核心流程、课程知识应用、运行方式和面试问答。";

export default function PortfolioExecutionPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const [project, setProject] = useState(null);
  const [executionPackage, setExecutionPackage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [copiedAll, setCopiedAll] = useState(false);
  const [downloadingCodex, setDownloadingCodex] = useState(false);
  const [copiedGuide, setCopiedGuide] = useState(null);
  const [handoffDownloaded, setHandoffDownloaded] = useState(
    () => window.localStorage.getItem(`codex-handoff-downloaded-${projectId}`) === "true",
  );

  useEffect(() => {
    Promise.all([
      portfolioAPI.getProject(projectId),
      portfolioAPI.getExecutionPackage(projectId),
    ])
      .then(([projectData, packageData]) => {
        setProject(projectData);
        setExecutionPackage(packageData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  const generate = async () => {
    if (executionPackage && !window.confirm("重新生成会替换当前执行包，是否继续？")) return;
    try {
      setGenerating(true);
      setError(null);
      const data = await portfolioAPI.generateExecutionPackage(projectId);
      setExecutionPackage(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const copyAll = async () => {
    await navigator.clipboard.writeText(executionPackage.markdown_content);
    setCopiedAll(true);
    window.setTimeout(() => setCopiedAll(false), 1600);
  };

  const downloadMarkdown = () => {
    const blob = new Blob([executionPackage.markdown_content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${project.title.replace(/[\\/:*?"<>|]/g, "-")}-AI执行包.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const downloadCodexPackage = async () => {
    try {
      setDownloadingCodex(true);
      setError(null);
      const blob = await portfolioAPI.downloadCodexPackage(project.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `portfolio-project-${project.id}-codex-handoff.zip`;
      anchor.click();
      URL.revokeObjectURL(url);
      window.localStorage.setItem(`codex-handoff-downloaded-${project.id}`, "true");
      setHandoffDownloaded(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloadingCodex(false);
    }
  };

  const copyGuideInstruction = async (key, instruction) => {
    try {
      await navigator.clipboard.writeText(instruction);
      setCopiedGuide(key);
      window.setTimeout(() => setCopiedGuide(null), 1600);
    } catch {
      setError("复制失败，请手动选择并复制指令")
    }
  };

  if (loading) return <div className="loading">加载 AI 项目执行包...</div>;
  if (!project) return <div className="error">{error || "作品项目不存在"}</div>;

  return (
    <div className="page portfolio-execution-page">
      <nav className="execution-breadcrumb">
        <Link to="/portfolio-projects">我的作品</Link>
        <span>/</span>
        <Link to={`/portfolio-projects/${project.id}`}>{project.title}</Link>
        <span>/ AI 项目执行包</span>
      </nav>

      <header className="execution-hero">
        <div>
          <small>OPTIONAL SOURCE LEARNING</small>
          <h1>源码学习与项目开发（可选）</h1>
          <p>只有当你想亲自运行项目或深入学习真实源码时，才需要把「{project.title}」交给 Codex 开发。</p>
        </div>
        <button className="btn btn-primary" disabled={generating} onClick={generate}>
          {generating ? "AI 正在生成，请稍候..." : executionPackage ? "重新生成执行包" : "生成执行包"}
        </button>
      </header>

      {error && <div className="execution-error">{error}</div>}

      <section className="execution-optional-note">
        <strong>这不是默认学习步骤</strong>
        <p>如果你只想理解作品，请返回<Link to={`/portfolio-projects/${project.id}/learn`}>作品学习指南</Link>。当前页面会真正生成开发资料，之后才可能得到属于当前作品的源码、模型和测试结果。</p>
      </section>

      <section className="execution-next-steps">
        <header>
          <div>
            <small>不会忘记的使用流程</small>
            <h2>接下来怎么做</h2>
          </div>
          <strong>
            {!executionPackage
              ? "当前：先生成执行包"
              : handoffDownloaded
                ? "当前：使用 Codex 开发"
                : "当前：下载 Codex 交付包"}
          </strong>
        </header>

        <ol className="execution-guide-flow">
          <li className={executionPackage ? "completed" : "active"}>
            <span>1</span>
            <div><strong>生成执行包</strong><small>准备需求、架构、任务和提示词</small></div>
          </li>
          <li className={handoffDownloaded ? "completed" : executionPackage ? "active" : ""}>
            <span>2</span>
            <div><strong>下载并解压 ZIP</strong><small>解压到一个新的空项目目录</small></div>
          </li>
          <li className={handoffDownloaded ? "active" : ""}>
            <span>3</span>
            <div><strong>使用 Codex 打开目录</strong><small>发送下面的启动指令，按阶段开发和测试</small></div>
          </li>
          <li>
            <span>4</span>
            <div><strong>完成后审查代码</strong><small>执行 CODE_REVIEW_PROMPT.md</small></div>
          </li>
          <li>
            <span>5</span>
            <div><strong>回传完成项目</strong><small>上传源码 ZIP，基于真实代码独立分析</small></div>
          </li>
          <li>
            <span>6</span>
            <div><strong>学习和准备面试</strong><small>查看真实代码讲解或执行 PROJECT_EXPLANATION_PROMPT.md</small></div>
          </li>
        </ol>

        <div className="execution-guide-prompts">
          <article>
            <div><strong>① 启动 Codex</strong><button className="btn btn-secondary btn-sm" onClick={() => copyGuideInstruction("start", codexStartInstruction)}>{copiedGuide === "start" ? "已复制" : "复制指令"}</button></div>
            <p>{codexStartInstruction}</p>
          </article>
          <article>
            <div><strong>② 项目完成后进行代码审查</strong><button className="btn btn-secondary btn-sm" onClick={() => copyGuideInstruction("review", codexReviewInstruction)}>{copiedGuide === "review" ? "已复制" : "复制指令"}</button></div>
            <p>{codexReviewInstruction}</p>
            <small>作用：检查真实实现、测试、风险和遗漏，并处理高优先级问题。</small>
          </article>
          <article>
            <div><strong>③ 审查完成后学习项目</strong><button className="btn btn-secondary btn-sm" onClick={() => copyGuideInstruction("explain", codexExplanationInstruction)}>{copiedGuide === "explain" ? "已复制" : "复制指令"}</button></div>
            <p>{codexExplanationInstruction}</p>
            <small>作用：讲解架构、核心代码、课程知识应用、运行方式和面试问答。</small>
          </article>
        </div>
        <div className="execution-code-return">
          <div>
            <strong>Codex 已经完成并审查项目？</strong>
            <span>把项目源码压缩成 ZIP，回传知识库生成基于真实代码的架构、流程和面试讲解。</span>
          </div>
          <Link className="btn btn-primary" to={`/portfolio-projects/${project.id}/code-analysis`}>
            上传完成项目
          </Link>
        </div>
      </section>

      {!executionPackage ? (
        <section className="card execution-empty">
          <h2>尚未生成执行包</h2>
          <p>生成后，你会得到完整项目说明、架构、接口、开发阶段、测试计划，以及可直接复制给 Codex 的提示词。</p>
          <button className="btn btn-primary" disabled={generating} onClick={generate}>
            {generating ? "生成中..." : "立即生成"}
          </button>
        </section>
      ) : (
        <>
          <div className="execution-toolbar">
            <span>更新时间：{new Date(executionPackage.updated_at).toLocaleString()}</span>
            <div>
              <button className="btn btn-secondary" onClick={copyAll}>{copiedAll ? "已复制" : "复制完整执行包"}</button>
              <button className="btn btn-success" onClick={downloadMarkdown}>下载 Markdown</button>
              <button className="btn btn-codex" disabled={downloadingCodex} onClick={downloadCodexPackage}>
                {downloadingCodex ? "正在打包..." : "下载 Codex 项目交付包"}
              </button>
            </div>
          </div>

          <ExecutionPackageSection title="Codex 完整开发提示词" copyText={executionPackage.codex_master_prompt} featured>
            <pre>{executionPackage.codex_master_prompt}</pre>
          </ExecutionPackageSection>

          <ExecutionPackageSection title="项目需求说明" copyText={executionPackage.project_brief}>
            <p>{executionPackage.project_brief}</p>
          </ExecutionPackageSection>

          <div className="execution-grid">
            <ExecutionPackageSection title="技术选择" copyText={executionPackage.technology_choices.map((item) => `${item.name}：${item.purpose}；${item.version_policy}`).join("\n")}>
              <ul>{executionPackage.technology_choices.map((item) => <li key={item.name}><strong>{item.name}</strong><span>{item.purpose}</span><small>{item.version_policy}</small></li>)}</ul>
            </ExecutionPackageSection>
            <ExecutionPackageSection title="系统架构" copyText={executionPackage.architecture}>
              <p>{executionPackage.architecture}</p>
            </ExecutionPackageSection>
          </div>

          <ExecutionPackageSection title="建议目录结构" copyText={executionPackage.directory_structure}>
            <pre>{executionPackage.directory_structure}</pre>
          </ExecutionPackageSection>

          <div className="execution-grid">
            <ExecutionPackageSection title="数据模型" copyText={JSON.stringify(executionPackage.data_models, null, 2)}>
              <ul>{executionPackage.data_models.map((model) => <li key={model.name}><strong>{model.name}</strong><span>{model.purpose}</span><small>{Array.isArray(model.fields) ? model.fields.join("；") : model.fields}</small></li>)}</ul>
            </ExecutionPackageSection>
            <ExecutionPackageSection title="API 设计" copyText={JSON.stringify(executionPackage.api_contracts, null, 2)}>
              <ul>{executionPackage.api_contracts.map((api, index) => <li key={`${api.method}-${api.path}-${index}`}><strong>{api.method} {api.path}</strong><span>{api.purpose}</span><small>请求：{api.request}；响应：{api.response}</small></li>)}</ul>
            </ExecutionPackageSection>
          </div>

          <section className="execution-phases">
            <h2>分阶段交给 Codex</h2>
            {executionPackage.implementation_phases.map((phase, index) => (
              <ExecutionPackageSection key={`${phase.title}-${index}`} title={`阶段 ${index + 1}：${phase.title}`} copyText={phase.codex_prompt}>
                <p>{phase.objective}</p>
                <h3>开发任务</h3>
                <ul>{phase.tasks.map((task) => <li key={task}>{task}</li>)}</ul>
                <h3>验收标准</h3>
                <ul>{phase.acceptance_criteria.map((item) => <li key={item}>{item}</li>)}</ul>
                <details><summary>查看阶段提示词</summary><pre>{phase.codex_prompt}</pre></details>
              </ExecutionPackageSection>
            ))}
          </section>

          <div className="execution-grid">
            <ExecutionPackageSection title="测试计划" copyText={executionPackage.test_plan.join("\n")}>
              <ul>{executionPackage.test_plan.map((item) => <li key={item}>{item}</li>)}</ul>
            </ExecutionPackageSection>
            <ExecutionPackageSection title="最终验收清单" copyText={executionPackage.acceptance_checklist.join("\n")}>
              <ul>{executionPackage.acceptance_checklist.map((item) => <li key={item}>{item}</li>)}</ul>
            </ExecutionPackageSection>
          </div>

          <ExecutionPackageSection title="README 编写要求" copyText={executionPackage.readme_requirements.join("\n")}>
            <ul>{executionPackage.readme_requirements.map((item) => <li key={item}>{item}</li>)}</ul>
          </ExecutionPackageSection>

          <div className="execution-grid">
            <ExecutionPackageSection title="完成后代码审查提示词" copyText={executionPackage.review_prompt}>
              <pre>{executionPackage.review_prompt}</pre>
            </ExecutionPackageSection>
            <ExecutionPackageSection title="项目讲解提示词" copyText={executionPackage.explanation_prompt} featured>
              <pre>{executionPackage.explanation_prompt}</pre>
            </ExecutionPackageSection>
          </div>
        </>
      )}
    </div>
  );
}
