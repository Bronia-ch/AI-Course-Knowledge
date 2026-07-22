import { useEffect, useState } from "react";
import { portfolioAPI } from "../services/api";
import "./PortfolioEvidence.css";

export default function PortfolioEvidence({ project, onProjectChange }) {
  const [profile, setProfile] = useState({
    github_url: "",
    demo_url: "",
    demo_video_url: "",
    screenshot_urls: "",
    highlights: [],
    technical_challenges: null,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setProfile({
      github_url: project.showcase.github_url || "",
      demo_url: project.showcase.demo_url || "",
      demo_video_url: project.showcase.demo_video_url || "",
      screenshot_urls: (project.showcase.screenshot_urls || []).join("\n"),
      // 旧版手工数据继续随请求保留，但不再要求用户维护。
      highlights: project.showcase.highlights || [],
      technical_challenges: project.showcase.technical_challenges || null,
    });
  }, [project.id, project.showcase]);

  const saveProfile = async (event) => {
    event.preventDefault();
    try {
      setSaving(true);
      setSaved(false);
      setError(null);
      const data = await portfolioAPI.updateShowcase(project.id, {
        ...profile,
        screenshot_urls: profile.screenshot_urls
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
      });
      onProjectChange(data);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field, value) => {
    setSaved(false);
    setProfile((current) => ({ ...current, [field]: value }));
  };

  return (
    <section className="portfolio-evidence-section">
      <div className="portfolio-publish-heading">
        <div>
          <span>OPTIONAL</span>
          <h2>发布信息</h2>
        </div>
        <p>项目亮点、技术难点、完成情况和验证证据由 Codex 根据真实代码自动生成。你只需在准备公开展示时补充以下链接。</p>
      </div>
      {error && <div className="portfolio-evidence-error">{error}</div>}

      <form className="card portfolio-showcase-form" onSubmit={saveProfile}>
        <div className="portfolio-evidence-grid">
          <label>
            GitHub 仓库地址
            <input value={profile.github_url} onChange={(event) => updateField("github_url", event.target.value)} placeholder="https://github.com/..." />
          </label>
          <label>
            在线演示地址
            <input value={profile.demo_url} onChange={(event) => updateField("demo_url", event.target.value)} placeholder="https://demo.example.com" />
          </label>
          <label>
            演示视频地址
            <input value={profile.demo_video_url} onChange={(event) => updateField("demo_video_url", event.target.value)} placeholder="https://www.bilibili.com/video/..." />
          </label>
          <label className="portfolio-screenshot-field">
            项目截图地址（每行一个）
            <textarea rows={3} value={profile.screenshot_urls} onChange={(event) => updateField("screenshot_urls", event.target.value)} placeholder={"https://.../screenshot-1.png\nhttps://.../screenshot-2.png"} />
          </label>
        </div>
        <div className="portfolio-publish-actions">
          <button className="btn btn-primary" disabled={saving} type="submit">
            {saving ? "保存中..." : "保存发布信息"}
          </button>
          {saved && <span>已保存</span>}
        </div>
      </form>
    </section>
  );
}
