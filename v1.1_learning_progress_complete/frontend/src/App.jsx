import { BrowserRouter, Routes, Route } from "react-router-dom";
import CourseListPage from "./pages/CourseListPage";
import CourseDetailPage from "./pages/CourseDetailPage";
import LessonDetailPage from "./pages/LessonDetailPage";
import "./App.css";

/**
 * 应用根组件 — 路由配置
 *
 * /                → 课程列表首页
 * /courses/:id     → 课程详情（章节/课节管理）
 * /lessons/:id     → 课节详情（音频/转录/分析）
 */
function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          <Route path="/" element={<CourseListPage />} />
          <Route path="/courses/:id" element={<CourseDetailPage />} />
          <Route path="/lessons/:id" element={<LessonDetailPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
