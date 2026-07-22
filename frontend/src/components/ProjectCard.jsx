import { useState, useEffect } from "react";
import { projectAPI } from "../services/api";

/**
 * 项目卡片 — 可折叠，展示技术栈和流程
 */
export default function ProjectCard({ project }) {
  const [open, setOpen] = useState(false);
  const [knowledgePoints, setKnowledgePoints] = useState([]);
  const [knowledgePointsLoaded, setKnowledgePointsLoaded] = useState(false);

  // 展开时加载关联知识点
  useEffect(() => {
    if (!open || knowledgePointsLoaded) return;

    const controller = new AbortController();

    projectAPI
      .listKnowledgePoints(project.id, controller.signal)
      .then((data) => {
        setKnowledgePoints(data);
        setKnowledgePointsLoaded(true);
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          console.error("加载关联知识点失败:", err);
        }
      });

    return () => controller.abort();
  }, [open, knowledgePointsLoaded, project.id]);

  let techStack = [];
  let workflow = [];

  try {
    techStack = JSON.parse(project.technology_stack || "[]");
    workflow = JSON.parse(project.workflow || "[]");
  } catch {
    /* ignore parse errors */
  }

  return (
    <div className="card" style={{ marginBottom: 10 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
        }}
        onClick={() => setOpen(!open)}
      >
        <h4 style={{ fontSize: "0.95rem" }}>{project.name}</h4>
        <span style={{ fontSize: "0.8rem", color: "#999" }}>
          {open ? "收起 ▴" : "展开 ▾"}
        </span>
      </div>

      {project.goal && (
        <p style={{ fontSize: "0.85rem", color: "#555", marginTop: 4 }}>
          <strong>目标：</strong>
          {project.goal}
        </p>
      )}

      {open && (
        <div style={{ marginTop: 12 }}>
          {project.input && (
            <p style={{ fontSize: "0.85rem", color: "#555", marginBottom: 4 }}>
              <strong>输入：</strong>
              {project.input}
            </p>
          )}
          {project.output && (
            <p style={{ fontSize: "0.85rem", color: "#555", marginBottom: 4 }}>
              <strong>输出：</strong>
              {project.output}
            </p>
          )}
          {techStack.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <strong style={{ fontSize: "0.85rem" }}>技术栈：</strong>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 4 }}>
                {techStack.map((t, i) => (
                  <span
                    key={i}
                    style={{
                      fontSize: "0.75rem",
                      padding: "2px 8px",
                      borderRadius: 4,
                      background: "#f0edff",
                      color: "#667eea",
                    }}
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}
          {knowledgePoints.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <strong style={{ fontSize: "0.85rem" }}>
                📚 关联知识点：
              </strong>
              <div style={{ marginTop: 8 }}>
                {knowledgePoints.map((kp) => (
                  <div
                    key={kp.id}
                    style={{
                      padding: "10px 12px",
                      marginBottom: 6,
                      background: "#fafafa",
                      borderRadius: 6,
                      borderLeft: "3px solid #667eea",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginBottom: 4,
                      }}
                    >
                      <span
                        style={{
                          fontSize: "0.85rem",
                          fontWeight: 600,
                          color: "#333",
                        }}
                      >
                        {kp.title}
                      </span>
                      {kp.category && (
                        <span
                          style={{
                            fontSize: "0.7rem",
                            padding: "1px 6px",
                            borderRadius: 4,
                            color: "#667eea",
                            background: "#f0edff",
                          }}
                        >
                          {kp.category}
                        </span>
                      )}
                    </div>
                    {kp.description && (
                      <p
                        style={{
                          fontSize: "0.8rem",
                          color: "#888",
                          margin: "2px 0",
                        }}
                      >
                        {kp.description}
                      </p>
                    )}
                    {kp.reason && (
                      <p
                        style={{
                          fontSize: "0.8rem",
                          color: "#555",
                          marginTop: 4,
                          fontStyle: "italic",
                        }}
                      >
                        💡 {kp.reason}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {workflow.length > 0 && (
            <div>
              <strong style={{ fontSize: "0.85rem" }}>
                  📌 实现流程：
              </strong>

              <div
                style={{
                  marginTop: 10,
                  paddingLeft: 8,
                }}
              >
                {workflow.map((step, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      marginBottom: 8,
                    }}
                  >
                    <div
                      style={{
                        width: 22,
                        height: 22,
                        borderRadius: "50%",
                        background: "#667eea",
                        color: "white",
                        fontSize: "0.75rem",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        marginRight: 8,
                      }}
                    >
                      {i + 1}
                    </div>

                    <span
                      style={{
                        fontSize: "0.85rem",
                        color: "#555",
                      }}
                    >
                      {step}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
