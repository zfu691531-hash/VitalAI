<div align="center">

# VitalAI / AIStu

### AI-Powered Smart Campus Platform for Student Care and Educational Administration

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-42B883.svg)](https://vuejs.org/)
[![Vite](https://img.shields.io/badge/Vite-5.x-646CFF.svg)](https://vitejs.dev/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1.svg)](https://www.mysql.com/)

**中文** | [English](#english-overview)

VitalAI 是一个面向校园场景的智能教务与学生关怀平台，融合 FastAPI、Vue 3、MySQL、Milvus、Neo4j、LangChain 和 LangGraph，提供学生画像、风险研判、校规问答、智能分组、成绩诊断和教师工作流辅助能力。

</div>

---

## 关键词

`AI education` `smart campus` `student care` `student risk assessment` `educational administration` `FastAPI` `Vue 3` `LangChain` `LangGraph` `Milvus` `Neo4j` `RAG` `Bayesian inference` `multi-agent system` `school rule assistant`

## 项目亮点

- 学生关怀智能研判：从情绪、社交、安全、家庭、学业、行为六个维度生成可解释风险画像。
- 多智能体分析链路：维度专家 Agent 分析单项风险，综合 Agent 输出教师可读的研判结论。
- 贝叶斯证据修正：将多源信号转化为先验、似然比和后验概率，减少单次事件造成的误判。
- 图谱增强洞察：通过 Neo4j 分析同伴关系、社交孤立、风险传播和隐性关联。
- 校规知识服务：基于 Milvus 向量检索和 RAG，为教师提供可引用的校规问答能力。
- 教师闭环复核：支持确认风险、标记误报、处置回写，让系统持续改进。
- 完整教务基础能力：学生、教师、班级、成绩、标签、导入导出、智能分班分组和 AI 教务工具。

## 功能模块

| 模块 | 能力 |
| --- | --- |
| 教务管理 | 学生、教师、班级、成绩、用户与权限管理 |
| 学生画像 | 标签体系、成长记录、关怀数据、风险信号和画像刷新 |
| 学生关怀 | 六维度风险研判、社交孤立识别、贝叶斯修正、多智能体综合分析 |
| 校规问答 | 校规录入、知识库重建、向量检索、RAG 问答、反馈闭环 |
| 智能分组 | 基于学生画像和规则约束的分组、分班与均衡优化 |
| AI 工具 | 评语生成、成绩诊断、通知润色、会议策划、模拟面试、纪律沟通建议 |
| 数据流转 | Excel 导入导出、演示数据脚本、审计记录和测试用例 |

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3, Vite, Element Plus, Pinia, Vue Router, Axios |
| 后端 | FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic |
| 数据库 | MySQL 8.0 |
| 向量检索 | Milvus, pymilvus |
| 图数据库 | Neo4j |
| AI 编排 | LangChain, LangGraph |
| 测试 | Pytest, backend test suite |
| 工程化 | One-click launcher, GitHub issue templates, documentation assets |

## 系统架构

```text
Vue 3 + Element Plus frontend
        |
        v
FastAPI backend APIs
        |
        v
Business services and schema guards
        |
        +-- MySQL / SQLAlchemy      primary data and audit records
        +-- Milvus                  school-rule vector retrieval
        +-- Neo4j                   relationship graph analysis
        +-- LangChain / LangGraph   AI tools and multi-agent workflows
```

### 学生关怀研判链路

```text
Data input
  -> signal extraction
  -> rule scoring
  -> Bayesian correction
  -> graph-enhanced evidence
  -> multi-agent analysis
  -> teacher review and feedback
```

<div align="center">
  <img src="docs/assets/care-architecture.png" alt="VitalAI student care architecture" width="680">
</div>

## 快速开始

### 环境要求

| 依赖 | 建议版本 | 用途 |
| --- | --- | --- |
| Python | 3.11+ | 后端运行环境 |
| Node.js | 18+ | 前端运行环境 |
| MySQL | 8.0+ | 主数据库 |
| Milvus | 2.x | 校规向量检索 |
| Neo4j | 5.x | 学生关系图谱 |

### 克隆项目

```bash
git clone https://github.com/zfu691531-hash/VitalAI.git
cd VitalAI
```

### 一键启动开发环境

```bash
python main.py
```

启动后默认访问：

- 前端：`http://127.0.0.1:5173`
- 后端 API 文档：`http://127.0.0.1:8000/docs`

### 后端单独启动

```bash
cd backend
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

初始化数据库：

```bash
mysql -u root -p < ../docs/init_database.sql
```

### 前端单独启动

```bash
cd frontend
npm install
npm run dev
```

生产构建：

```bash
npm run build
```

## 配置说明

后端配置文件来自 `backend/.env.example`，主要包含：

| 配置 | 说明 |
| --- | --- |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | MySQL 连接配置 |
| `JWT_SECRET`, `JWT_EXPIRE_MINUTES` | 登录认证配置 |
| `AI_API_BASE_URL`, `AI_API_KEY`, `AI_MODEL_NAME` | AI 模型服务配置 |
| `AI_EMBEDDING_MODEL_NAME`, `AI_EMBEDDING_DIM` | 向量嵌入配置 |
| `MILVUS_URI`, `MILVUS_COLLECTION` | Milvus 校规知识库配置 |
| `APP_HOST`, `APP_PORT`, `DEBUG` | 后端服务配置 |

## 演示账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `admin123` | 管理员 |
| `wang_math` | `teacher123` | 教师 |
| `stu_2024001` | `student123` | 学生 |

更多演示说明见 [docs/演示账号与案例说明-2026-04-10.md](docs/演示账号与案例说明-2026-04-10.md)。

## 项目结构

```text
VitalAI/
  backend/
    api/                    FastAPI route handlers
    services/               business logic and AI workflows
      ai/                   AI teaching tools
      rag/                  school-rule retrieval and RAG services
    schemas/                Pydantic request and response models
    core/                   settings, security and common response helpers
    database/models/        SQLAlchemy ORM models
    scripts/                seed and demo data scripts
    tests/                  backend test suite
  frontend/
    src/views/              page-level Vue views
    src/components/         reusable UI components
    src/stores/             Pinia stores
    src/router/             route definitions
    src/api/                API client modules
    src/utils/              shared utilities
  docs/                     architecture, test reports and product documents
  main.py                   one-click local launcher
```

## 核心代码入口

| 文件 | 说明 |
| --- | --- |
| `backend/main.py` | FastAPI 应用入口、路由注册、生命周期钩子 |
| `backend/services/student_care_service.py` | 学生关怀画像构建、基础评分、刷新逻辑 |
| `backend/services/student_care_bayes_service.py` | 贝叶斯风险修正和证据处理 |
| `backend/services/student_care_agent_service.py` | 多智能体研判、综合结论和复核统计 |
| `backend/services/student_care_isolation_service.py` | 社交孤立专项分析 |
| `backend/services/student_care_graph_service.py` | Neo4j 图谱信号生成 |
| `backend/services/rag/teacher_rule_assistant_service.py` | 校规问答和教师规则助手 |
| `frontend/src/views/student/StudentCareEvaluationPage.vue` | 学生关怀研判页面 |
| `frontend/src/views/ai/TeacherRuleAssistant.vue` | 校规智能问答页面 |

## 文档

| 文档 | 内容 |
| --- | --- |
| [项目技术架构总览](docs/项目技术架构总览.md) | 总体架构、模块边界和技术选型 |
| [学生关怀智能研判体系设计](docs/学生关怀智能研判体系设计.md) | 学生关怀业务闭环和分层设计 |
| [学生关怀关键技术亮点说明](docs/学生关怀关键技术亮点说明.md) | 演示与答辩可用的技术亮点 |
| [学生关怀多智能体风险研判方案](docs/学生关怀多智能体风险研判方案.md) | 多智能体分析方法和流程 |
| [学生画像应用场景全景图](docs/学生画像应用场景全景图.md) | 学生画像在校园业务中的应用 |
| [后端整体测试报告](docs/后端整体测试报告-2026-04-10.md) | 后端测试覆盖和验证结果 |
| [数据库初始化 SQL](docs/init_database.sql) | 数据库表结构和初始化脚本 |

## 测试

后端测试：

```bash
cd backend
pytest
```

前端构建验证：

```bash
cd frontend
npm run build
```

## English Overview

VitalAI, also named AIStu in the codebase, is an AI-powered smart campus platform for K-12 educational administration and student care. It combines traditional school management workflows with explainable student risk assessment, Bayesian evidence correction, graph-based relationship analysis, vector-search school rule Q&A, and multi-agent AI reasoning.

The project is built with FastAPI, Vue 3, MySQL, Milvus, Neo4j, LangChain, and LangGraph. It is suitable for demos, research prototypes, graduation projects, and practical exploration of AI-assisted education systems.

Core capabilities:

- Student, teacher, class, score and tag management.
- Explainable six-dimension student care assessment.
- Bayesian risk correction for multi-source evidence.
- Neo4j-powered social isolation and relationship analysis.
- Milvus-backed RAG for school rule search and teacher Q&A.
- AI teaching tools for comments, score diagnosis, notices, meetings and discipline communication.
- Teacher review loop for risk confirmation, false-positive handling and continuous improvement.

## GitHub 搜索建议

如果你拥有仓库管理权限，建议在 GitHub 仓库页面补充：

- Description: `AI-powered smart campus platform for student care, school rule RAG, Bayesian risk assessment and educational administration.`
- Website: 可以填写项目演示地址或后端 API 文档地址。
- Topics: `ai-education`, `smart-campus`, `student-care`, `fastapi`, `vue3`, `langchain`, `langgraph`, `milvus`, `neo4j`, `rag`, `bayesian-inference`, `education-management`

## 免责声明

学生关怀和风险识别功能用于辅助教师决策，不能替代教师判断、心理健康专业评估或学校正式处置流程。公开演示时请使用脱敏数据或仓库提供的演示数据。

## License

This project is licensed under the [MIT License](LICENSE).
