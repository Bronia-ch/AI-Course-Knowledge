/**
 * API 请求层 — 封装所有后端 21 个端点
 *
 * 约定：
 *   - 所有请求以 /api 开头（Vite proxy 转发到后端 localhost:8000）
 *   - 响应优先解析为 JSON，也兼容纯文本和空响应
 *   - 非 2xx 响应抛出带 message 的 Error
 */

const BASE = "/api";

async function parseResponse(res) {
  const text = await res.text();
  if (!text) return null;

  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      return JSON.parse(text);
    } catch {
      throw new Error(`服务器返回了无效的 JSON (${res.status})`);
    }
  }

  return text;
}

function getErrorMessage(data, fallback) {
  if (typeof data === "string" && data.trim()) return data;
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail)) {
    const messages = data.detail
      .map((item) => item?.msg)
      .filter(Boolean);
    if (messages.length > 0) return messages.join("；");
  }
  return fallback;
}

/**
 * 通用请求函数
 * @param {string} method - HTTP 方法
 * @param {string} path - 请求路径（如 /courses）
 * @param {object} [body] - 请求体（仅 POST/PUT）
 * @returns {Promise<object>} 解析后的 JSON 响应
 */
async function request(method, path, body, fetchOptions = {}) {
  const opts = {
    ...fetchOptions,
    method,
    headers: { ...(fetchOptions.headers || {}) },
  };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(BASE + path, opts);

  const data = await parseResponse(res);
  if (!res.ok) {
    throw new Error(getErrorMessage(data, `请求失败 (${res.status})`));
  }
  return data;
}

/**
 * 上传文件（FormData）
 * @param {string} path - 请求路径
 * @param {FormData} formData - 包含文件的表单数据
 * @returns {Promise<object>}
 */
async function uploadFile(path, formData) {
  const res = await fetch(BASE + path, {
    method: "POST",
    body: formData,
  });
  const data = await parseResponse(res);
  if (!res.ok) {
    throw new Error(getErrorMessage(data, `上传失败 (${res.status})`));
  }
  return data;
}

async function downloadFile(path) {
  const res = await fetch(BASE + path);
  if (!res.ok) {
    const data = await parseResponse(res);
    throw new Error(getErrorMessage(data, `下载失败 (${res.status})`));
  }
  return res.blob();
}

// =========================================================================
// 课程 API
// =========================================================================
export const courseAPI = {
  list: () => request("GET", "/courses"),
  get: (id) => request("GET", `/courses/${id}`),
  getTree: (id) => request("GET", `/courses/${id}/tree`),
  create: (data) => request("POST", "/courses", data),
  update: (id, data) => request("PUT", `/courses/${id}`, data),
  delete: (id) => request("DELETE", `/courses/${id}`),
};

// =========================================================================
// 章节 API
// =========================================================================
export const chapterAPI = {
  listByCourse: (courseId) => request("GET", `/chapters?course_id=${courseId}`),
  get: (id) => request("GET", `/chapters/${id}`),
  create: (data) => request("POST", "/chapters", data),
  update: (id, data) => request("PUT", `/chapters/${id}`, data),
  delete: (id) => request("DELETE", `/chapters/${id}`),
};

// =========================================================================
// 课节 API
// =========================================================================
export const lessonAPI = {
  listByChapter: (chapterId) =>
    request("GET", `/lessons?chapter_id=${chapterId}`),
  get: (id) => request("GET", `/lessons/${id}`),
  create: (data) => request("POST", "/lessons", data),
  update: (id, data) => request("PUT", `/lessons/${id}`, data),
  delete: (id) => request("DELETE", `/lessons/${id}`),
};

// =========================================================================
// 音频上传 API
// =========================================================================
export const uploadAPI = {
  upload: (lessonId, file) => {
    const fd = new FormData();
    fd.append("file", file);
    return uploadFile(`/lessons/${lessonId}/upload-audio`, fd);
  },
  getInfo: (lessonId) => request("GET", `/lessons/${lessonId}/audio`),
  delete: (lessonId) => request("DELETE", `/lessons/${lessonId}/audio`),
};

// =========================================================================
// 转录 API
// =========================================================================
export const transcriptionAPI = {
  start: (lessonId) => request("POST", `/lessons/${lessonId}/transcribe`),
};

// =========================================================================
// 转录数据 API
// =========================================================================
export const transcriptAPI = {
  listByLesson: (lessonId) =>
    request("GET", `/lessons/${lessonId}/transcripts`),
};

// =========================================================================
// 知识点 API
// =========================================================================
export const knowledgePointAPI = {
  listByLesson: (lessonId) =>
    request("GET", `/lessons/${lessonId}/knowledge-points`),
};

// =========================================================================
// 项目 API
// =========================================================================
export const projectAPI = {
  listByLesson: (lessonId) =>
    request("GET", `/lessons/${lessonId}/projects`),
  listKnowledgePoints: (projectId, signal) =>
    request("GET", `/projects/${projectId}/knowledge-points`, undefined, { signal }),
};

// =========================================================================
// 学习进度 API
// =========================================================================
export const progressAPI = {
  get: (lessonId) => request("GET", `/lessons/${lessonId}/progress`),
  save: (lessonId, data) => request("POST", `/lessons/${lessonId}/progress`, data),
};

// =========================================================================
// AI 学习助手 API
// =========================================================================
export const assistantAPI = {
  ask: (lessonId, question) =>
    request("POST", `/lessons/${lessonId}/ask`, { question }),
};

// =========================================================================
// 面试作品机会 API
// =========================================================================
export const portfolioAPI = {
  getOverview: () => request("GET", "/portfolio-overview"),
  listProjects: () => request("GET", "/portfolio-projects"),
  listOpportunities: (chapterId) =>
    request("GET", `/chapters/${chapterId}/portfolio-opportunities`),
  generateOpportunities: (chapterId) =>
    request("POST", `/chapters/${chapterId}/portfolio-opportunities/generate`),
  createProject: (opportunityId) =>
    request("POST", `/portfolio-opportunities/${opportunityId}/create-project`),
  getProject: (projectId) =>
    request("GET", `/portfolio-projects/${projectId}`),
  completeLearning: (projectId) =>
    request("POST", `/portfolio-projects/${projectId}/learning-completions`),
  getConceptGuide: (projectId) =>
    request("GET", `/portfolio-projects/${projectId}/concept-guide`),
  updateTask: (taskId, status) =>
    request("PATCH", `/portfolio-project-tasks/${taskId}`, { status }),
  updateShowcase: (projectId, data) =>
    request("PUT", `/portfolio-projects/${projectId}/showcase`, data),
  createEvidence: (projectId, data) =>
    request("POST", `/portfolio-projects/${projectId}/evidences`, data),
  deleteEvidence: (evidenceId) =>
    request("DELETE", `/portfolio-evidences/${evidenceId}`),
  getExecutionPackage: (projectId) =>
    request("GET", `/portfolio-projects/${projectId}/execution-package`),
  generateExecutionPackage: (projectId) =>
    request("POST", `/portfolio-projects/${projectId}/execution-package/generate`),
  downloadCodexPackage: (projectId) =>
    downloadFile(`/portfolio-projects/${projectId}/execution-package/codex-zip`),
  getCodeAnalysis: (projectId) =>
    request("GET", `/portfolio-projects/${projectId}/code-analysis`),
  importCodexAnalysis: (projectId, data) =>
    request("POST", `/portfolio-projects/${projectId}/code-analysis/import`, data),
};

// =========================================================================
// 分析 API
// =========================================================================
export const analysisAPI = {
  start: (lessonId) => request("POST", `/lessons/${lessonId}/analyze`),
};
