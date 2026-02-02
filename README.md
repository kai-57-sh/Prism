# Prism 项目配置说明

## 系统架构

本系统由 FastAPI 后端编排，核心能力依赖两个外部 API 服务：

1. **Wan2.6-t2v (阿里云 DashScope)** - 文本生成视频
2. **Qwen3-235B-A22B-Instruct-2507 (魔搭社区 ModelScope)** - 大语言模型

后端负责输入处理、IR 解析、模板匹配/实例化、分镜生成、FFmpeg 拆分音视频与静态资源输出；Redis 用于限流、并发控制与 RQ 队列；SQLite 保存作业状态。前端包含：

- **React + Vite Web UI**：位于 `frontend/`
- **Gradio 测试 UI（可选）**：位于 `frontend-test/`

## 环境配置

### 必需的 API 密钥

#### 1. DashScope API Key (阿里云)

**用途**: Wan2.6-t2v 视频生成

**获取方式**:
- 访问: https://help.aliyun.com/zh/model-studio/get-api-key
- 登录阿里云账号
- 创建 API Key

**环境变量**:
```bash
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx
```

#### 2. ModelScope API Key (魔搭社区)

**用途**: Qwen3-235B-A22B-Instruct-2507 语言模型

**获取方式**:
- 访问: https://modelscope.cn/my/myaccesstoken
- 登录魔搭社区账号
- 生成 Access Token（格式: `ms-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`）

**环境变量**:
```bash
MODELSCOPE_API_KEY=ms-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1
QWEN_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
```

### 配置文件

- 后端默认读取 `backend/.env`（`backend/run_dev.sh` 会强制要求该文件）
- 推荐复制示例配置：`cp .env.example backend/.env`
- React 前端读取 `frontend/.env`（用于 `VITE_LOGIN_PASSWORD`；未设置时默认 `prism`）
- Gradio 测试 UI 使用 `BACKEND_URL` 环境变量（默认 `http://localhost:8000`）

### 其他常用配置

完整变量列表见 `.env.example`，常用项包括：

```bash
# Database / Redis
DATABASE_URL=sqlite:///./data/jobs.db
REDIS_URL=redis://localhost:6379/0

# Static storage (默认 /var/lib/prism/static，若无权限会回退到 backend/data)
STATIC_ROOT=/var/lib/prism/static
STATIC_VIDEO_SUBDIR=vedios
STATIC_AUDIO_SUBDIR=audio
STATIC_METADATA_SUBDIR=metadata

# Application
APP_ENV=development
LOG_LEVEL=INFO

# Template matching
TEMPLATE_MATCH_MIN_CONFIDENCE=0.5

# Rate limiting
RATE_LIMIT_PER_MIN=10
RATE_LIMIT_BURST=10
RATE_LIMIT_WINDOW_S=60
MAX_CONCURRENT_JOBS_PER_IP=5

# Quality Modes
DEFAULT_QUALITY_MODE=balanced

# Job Retention
JOB_RETENTION_DAYS=30

# Frontend Login (Vite)
VITE_LOGIN_PASSWORD=prism

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

> 说明：`RQ_QUEUE_NAME` 默认为 `prism`，用于 `/render` 队列，可按需设置。

## 快速开始

### 1. 安装依赖

```bash
# 后端依赖（Python >= 3.11）
pip install -r backend/requirements.txt

# 前端依赖（React + Vite）
cd frontend
npm install

# 可选：Gradio 测试 UI 依赖
pip install -r frontend-test/requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example backend/.env
```

编辑 `backend/.env` 填入 API Key。前端登录密码可在 `frontend/.env` 中配置：

```bash
VITE_LOGIN_PASSWORD=prism
```

### 3. 启动依赖服务

确保 Redis 正常运行（地址与 `REDIS_URL` 对应）。

### 4. 启动后端

```bash
cd backend
./run_dev.sh
```

如需启用 `/render` 异步渲染（前端默认流程会调用），另开终端启动 RQ worker：

```bash
cd backend
./run_worker.sh
```

后端默认运行在 `http://localhost:8000`

- API 文档: `http://localhost:8000/docs`
- 数据库文件: `backend/data/jobs.db`

### 5. 启动前端

#### React Web UI（推荐）

```bash
cd frontend
npm run dev
```

前端默认运行在 `http://localhost:5173`，已配置 `/api` 代理到后端 `http://localhost:8000`。

#### Gradio 测试 UI（可选）

```bash
cd frontend-test
./run_dev.sh
```

前端默认运行在 `http://localhost:7860`，可通过 `BACKEND_URL` 指定后端地址。

## 使用流程（Web UI）

1. 输入需求并提交，生成脚本与分镜（`/plan`）
2. 需要修改时直接输入反馈（`/revise`）
3. 点击“生成视频”触发渲染（`/render`，需要 RQ worker）
4. 通过 `/v1/t2v/jobs/{job_id}` 查询状态与资源

## Docker Compose 部署

```bash
cd docker
# 确保已设置 DASHSCOPE_API_KEY / MODELSCOPE_API_KEY 等环境变量
docker-compose up --build
```

访问：
- 前端入口: `http://localhost:7860`
- 后端 API: `http://localhost:7860/v1/t2v/`
- 静态资源: `http://localhost:7860/static/vedios/...`

> 说明：`/docs` 未在 Nginx 中转发，如需访问后端文档，请额外暴露 `backend:8000` 或修改 `docker/nginx.conf`。

## 故障排查

#### 后端无法启动

- 检查 `backend/.env` 是否存在且包含有效的 API 密钥
- 确保端口 8000 未被占用: `lsof -i :8000`
- 查看日志输出中的错误信息

#### 前端无法连接后端

- React UI（`frontend/`）：确认 `http://localhost:8000` 可访问，检查 `frontend/vite.config.ts` 代理配置
- Gradio UI（`frontend-test/`）：检查 `BACKEND_URL` 环境变量

#### 渲染请求卡住或无响应

- 确认 Redis 正常运行
- 确认已启动 `backend/run_worker.sh`（`/render` 依赖 RQ worker）

#### 数据库错误

- SQLite 数据库会自动创建在 `backend/data/jobs.db`
- 如果出现数据库锁定，删除数据库文件并重启后端

## API 测试

### 测试视频生成 (Wan2.6-t2v)

```bash
python docs/reference-pre/wan2.6.py
```

### 测试语言模型 (Qwen3-235B)

```bash
python docs/reference-pre/Qwen3-235B-A22B-Instruct-2507.py
```

## 技术栈

### 后端

- **框架**: FastAPI 0.104+
- **LLM 集成**: LangChain 0.1+
- **视频生成**: DashScope SDK (Wan2.6-t2v)
- **语言模型**: ModelScope (Qwen3-235B-A22B-Instruct-2507) via OpenAI-compatible endpoint
- **任务队列**: RQ + Redis
- **数据库**: SQLAlchemy + SQLite
- **限流与并发控制**: Redis
- **向量搜索**: FAISS
- **媒体处理**: FFmpeg

### 前端

- **React + Vite**
- **Tailwind CSS + Framer Motion**
- **可选 Gradio UI**（frontend-test）

### 关键依赖

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
langchain==0.1.0
langchain-openai==0.0.2
dashscope==1.25.9
openai>=1.0.0
pydantic==2.5.2
pydantic-settings==2.1.0
sqlalchemy==2.0.23
alembic==1.13.0
redis==5.0.1
rq==1.15.1
faiss-cpu==1.7.4
jinja2==3.1.2
structlog==23.2.0
aiofiles==23.2.1
httpx==0.25.2
```

## 项目结构

```
backend/
├── src/
│   ├── api/              # FastAPI 路由
│   ├── core/             # 核心业务逻辑
│   ├── models/           # 数据模型
│   ├── services/         # 服务层
│   ├── config/           # 配置管理
│   ├── templates/        # 医疗场景模板
│   └── workers/          # RQ 任务
├── tests/                # 测试文件
├── requirements.txt      # Python 依赖
└── .env                  # 环境变量配置

frontend/
├── src/                  # React + Vite Web UI
├── public/
└── package.json

frontend-test/
├── src/                  # Gradio UI
├── requirements.txt
└── run_dev.sh

docker/
└── docker-compose.yml    # Nginx/后端/前端编排

scripts/                  # 本地开发与部署脚本

docs/
├── api.md
├── PIPELINE.md
├── backend-dataflow.md
├── llm_orchestrator_llm_prompts.md
├── wan26-migration-summary.md
└── reference-pre/
```

## 参考文档

- `docs/api.md`
- `docs/PIPELINE.md`
- `docs/backend-dataflow.md`
- `docs/llm_orchestrator_llm_prompts.md`
- `docs/wan26-migration-summary.md`

## 支持与帮助

- DashScope 文档: https://help.aliyun.com/zh/model-studio
- ModelScope 文档: https://modelscope.cn/docs
- LangChain 文档: https://python.langchain.com/
