# Prism 项目配置说明

## 系统架构

本系统由 FastAPI 后端编排，核心能力依赖两个外部 API 服务：

1. **Wan2.6-t2v (阿里云 DashScope)** - 文本生成视频
2. **Qwen3-235B-A22B-Instruct-2507 (魔搭社区 ModelScope)** - 大语言模型

后端负责输入处理、IR 解析、模板匹配/实例化、分镜生成、FFmpeg 拆分音视频与静态资源输出；Redis 用于限流与并发控制，SQLite 保存作业状态。

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

### 其他常用配置

后端默认读取 `backend/.env`（`backend/run_dev.sh` 会强制要求该文件）。推荐复制示例配置：

```bash
cp .env.example backend/.env
```

常用环境变量（完整列表请看 `.env.example`）：

```bash
# Database / Redis
DATABASE_URL=sqlite:///./data/jobs.db
REDIS_URL=redis://localhost:6379/0

# Static storage (默认 /var/lib/prism/static，若无权限会回退到 backend/data)
STATIC_ROOT=/var/lib/prism/static
STATIC_VIDEO_SUBDIR=vedios
STATIC_AUDIO_SUBDIR=audio
STATIC_METADATA_SUBDIR=metadata

# FFmpeg
FFMPEG_PATH=ffmpeg

# Template matching
EMBEDDING_MODEL=text-embedding-v2
TEMPLATE_MATCH_MIN_CONFIDENCE=0.5
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 到 `backend/.env` 并填入 API 密钥：

```bash
cp .env.example backend/.env
```

编辑 `backend/.env` 文件：

```bash
# DashScope API Key (阿里云)
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# ModelScope API Key (魔搭社区)
MODELSCOPE_API_KEY=ms-your_modelscope_token_here

# ModelScope API 配置
MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1
QWEN_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
```

### 3. 启动服务

```bash
cd backend
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## 本地开发 (Local Development)

### 快速启动 (推荐)

使用提供的开发脚本快速启动前后端服务：

#### 1. 启动后端服务

```bash
cd backend
./run_dev.sh
```

后端将运行在 `http://localhost:8000`

- API 文档: http://localhost:8000/docs
- 数据库文件: `backend/data/jobs.db`
- 依赖服务: Redis（`REDIS_URL`），FFmpeg（`FFMPEG_PATH`）

#### 2. 启动前端服务 (可选)

在新终端中运行：

```bash
cd frontend
./run_dev.sh
```

前端将运行在 `http://localhost:7860`

### 手动启动

#### 启动后端

```bash
cd backend

# 确保 .env 文件已配置
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### 启动前端

```bash
cd frontend

# 设置后端 URL (可选，默认为 http://localhost:8000)
export BACKEND_URL=http://localhost:8000

# 启动 Gradio
gradio src/app.py
```

### 前端环境变量

创建 `frontend/.env` 文件配置前端：

```bash
# 复制示例配置
cp frontend/.env.example frontend/.env

# 编辑配置（可选，默认为 localhost:8000）
# BACKEND_URL=http://localhost:8000
```

### 测试前端-后端集成

1. **访问前端**: http://localhost:7860
2. **生成视频**:
   - 在 "Generate" 标签页输入提示词
   - 选择质量模式和分辨率
   - 点击 "Generate"
   - 查看返回的 Job ID
3. **检查状态**:
   - 在 "Generate" 标签页点击 "Check Status"
   - 查看生成进度和预览资源
4. **定稿视频**:
   - 选择预览候选版本
   - 点击 "Finalize Selected" 生成最终视频
5. **修订视频**:
   - 在 "Refine" 标签页输入 Job ID
   - 提供修订反馈
   - 查看修订后的结果

### Docker Compose 部署

如果本地开发遇到问题，可以使用 Docker Compose：

```bash
cd docker

# 确保 .env 文件已配置
docker-compose up --build
```

访问：
- 前端: http://localhost:80
- 后端 API: http://localhost:80/v1/t2v/
- 静态资源: http://localhost:80/static/vedios/...
- 后端文档: Nginx 默认不转发 `/docs`，需直连后端或调整配置

### 故障排查

#### 后端无法启动

- 检查 `.env` 文件是否存在且包含有效的 API 密钥
- 确保端口 8000 未被占用: `lsof -i :8000`
- 查看日志输出中的错误信息

#### 前端无法连接后端

- 确保后端正在运行: `curl http://localhost:8000/docs`
- 检查 `BACKEND_URL` 环境变量设置
- 查看浏览器控制台的网络请求错误

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
- **视频生成**: DashScope SDK (wan2.6-t2v)
- **语言模型**: ModelScope (Qwen3-235B-A22B-Instruct-2507) via OpenAI-compatible endpoint
- **数据库**: SQLAlchemy + SQLite
- **限流与并发控制**: Redis
- **向量搜索**: FAISS
- **媒体处理**: FFmpeg

### 关键依赖

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
langchain==0.1.0
langchain-openai==0.0.2
langchain-community==0.0.10
dashscope==1.25.9
openai>=1.0.0
pydantic==2.5.2
pydantic-settings==2.1.0
sqlalchemy==2.0.23
alembic==1.13.0
redis==5.0.1
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
│   │   ├── wan26_adapter.py          # Wan2.6-t2v 适配器
│   │   ├── llm_orchestrator.py       # LLM 编排器
│   │   ├── input_processor.py        # 输入处理器
│   │   ├── template_router.py        # 模板路由器
│   │   ├── prompt_compiler.py        # Prompt 编译
│   │   └── validator.py              # 参数校验
│   ├── models/           # 数据模型
│   ├── services/         # 服务层
│   ├── config/           # 配置管理
│   ├── templates/        # 医疗场景模板
│   └── utils/            # 工具函数
├── tests/                # 测试文件
├── requirements.txt      # Python 依赖
└── .env                  # 环境变量配置

frontend/
├── src/                  # Gradio UI
└── requirements.txt      # Python 依赖

docker/
└── docker-compose.yml    # Nginx/后端/前端编排

scripts/                  # 本地开发与部署脚本

docs/
├── reference-pre/        # API 参考示例
│   ├── wan2.6.py
│   └── Qwen3-235B-A22B-Instruct-2507.py
└── wan26-migration-summary.md  # 详细集成文档
```

## 参考文档

- **Wan2.6-t2v 集成**: `docs/reference-pre/wan2.6.py`
- **Qwen3-235B 集成**: `docs/reference-pre/Qwen3-235B-A22B-Instruct-2507.py`
- **详细技术文档**: `docs/wan26-migration-summary.md`

## 支持与帮助

- DashScope 文档: https://help.aliyun.com/zh/model-studio
- ModelScope 文档: https://modelscope.cn/docs
- LangChain 文档: https://python.langchain.com/
