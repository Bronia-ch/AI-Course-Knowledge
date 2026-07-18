# AI课程知识库

个人AI课程管理工具 —— 上传课程音频，AI自动分析并生成结构化知识笔记。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python + FastAPI + SQLAlchemy |
| 数据库 | SQLite |
| 前端 | React + Vite |
| AI模块（规划中） | faster-whisper + DeepSeek API |

## 目录结构

```
├── backend/                # 后端（FastAPI）
│   ├── app/
│   │   ├── main.py         # 应用入口
│   │   ├── config.py       # 配置管理
│   │   ├── database.py     # 数据库连接
│   │   ├── models/         # 数据模型
│   │   ├── routers/        # API路由
│   │   ├── services/       # 业务逻辑
│   │   └── ai/             # AI分析模块
│   ├── requirements.txt
│   └── venv_setup.md
├── frontend/               # 前端（React + Vite）
│   ├── src/
│   │   ├── main.jsx        # 入口文件
│   │   ├── App.jsx         # 根组件
│   │   ├── pages/          # 页面组件
│   │   ├── components/     # 通用组件
│   │   ├── services/       # API调用层
│   │   └── stores/         # 状态管理
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 快速启动

### 1. 后端

```bash
cd backend

# 创建虚拟环境（详见 venv_setup.md）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务（开发模式，自动重载）
uvicorn app.main:app --reload
```

访问 http://localhost:8000/docs 查看 API 文档。

### 2. 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5173 查看前端页面。

## 开发阶段

- [x] 项目初始化
- [ ] 数据库模型设计
- [ ] 课程管理 CRUD API
- [ ] 音频上传功能
- [ ] AI 语音转文字（faster-whisper）
- [ ] AI 知识笔记生成（DeepSeek API）
- [ ] 前端课程管理界面
- [ ] 前端知识笔记展示
