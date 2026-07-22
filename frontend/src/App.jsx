import { BrowserRouter, Routes, Route } from "react-router-dom";
import CourseListPage from "./pages/CourseListPage";
import CourseDetailPage from "./pages/CourseDetailPage";
import LessonDetailPage from "./pages/LessonDetailPage";
import PortfolioProjectPage from "./pages/PortfolioProjectPage";
import PortfolioProjectListPage from "./pages/PortfolioProjectListPage";
import PortfolioShowcasePage from "./pages/PortfolioShowcasePage";
import PortfolioExecutionPage from "./pages/PortfolioExecutionPage";
import PortfolioCodeAnalysisPage from "./pages/PortfolioCodeAnalysisPage";
import PortfolioOverviewPage from "./pages/PortfolioOverviewPage";
import "./App.css";

/**
 * 应用根组件 — 路由配置
 *
 * /                → 课程列表首页
 * /courses/:id     → 课程详情（章节/课节管理）
 * /lessons/:id     → 课节详情（音频/转录/分析）
 * /portfolio-projects → 我的作品项目列表
 * /portfolio-overview → 个人能力作品集总览
 * /portfolio-projects/:id → 作品项目计划详情
 * /portfolio-projects/:id/showcase → 面试展示页
 * /portfolio-projects/:id/execution → AI 项目执行包
 * /portfolio-projects/:id/code-analysis → 完成项目真实代码讲解
 */
function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          <Route path="/" element={<CourseListPage />} />
          <Route path="/courses/:id" element={<CourseDetailPage />} />
          <Route path="/lessons/:id" element={<LessonDetailPage />} />
          <Route
            path="/portfolio-projects"
            element={<PortfolioProjectListPage />}
          />
          <Route path="/portfolio-overview" element={<PortfolioOverviewPage />} />
          <Route
            path="/portfolio-projects/:id"
            element={<PortfolioProjectPage />}
          />
          <Route
            path="/portfolio-projects/:id/showcase"
            element={<PortfolioShowcasePage />}
          />
          <Route
            path="/portfolio-projects/:id/execution"
            element={<PortfolioExecutionPage />}
          />
          <Route
            path="/portfolio-projects/:id/code-analysis"
            element={<PortfolioCodeAnalysisPage />}
          />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
