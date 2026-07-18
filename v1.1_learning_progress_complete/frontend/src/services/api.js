/**
 * API 请求层 — 封装所有后端 21 个端点
 *
 * 约定：
 *   - 所有请求以 /api 开头（Vite proxy 转发到后端 localhost:8000）
 *   - 响应自动解析为 JSON
 *   - 非 2xx 响应抛出带 message 的 Error
 */

const BASE = "/api";

/**
 * 通用请求函数
 * @param {string} method - HTTP 方法
 * @param {string} path - 请求路径（如 /courses）
 * @param {object} [body] - 请求体（仅 POST/PUT）
 * @returns {Promise<object>} 解析后的 JSON 响应
 */
async function request(method, path, body) {
  const opts = {
    method,
    headers: {},
  };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(BASE + path, opts);

  // 204 No Content
  if (res.status === 204) return null;

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `请求失败 (${res.status})`);
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
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || `上传失败 (${res.status})`);
  }
  return res.json();
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
};

// =========================================================================
// 学习进度 API
// =========================================================================
export const progressAPI = {
  get: (lessonId) => request("GET", `/lessons/${lessonId}/progress`),
  save: (lessonId, data) => request("POST", `/lessons/${lessonId}/progress`, data),
};

// =========================================================================
// 分析 API
// =========================================================================
export const analysisAPI = {
  start: (lessonId) => request("POST", `/lessons/${lessonId}/analyze`),
};
