# Prism 项目实施翻盘手册

> 本文档记录了 Prism 项目在实施过程中遇到的问题及其解决方案,方便团队成员快速定位和解决类似问题。

**最后更新**: 2026-02-02
**项目**: Prism - AI 视频生成系统
**技术栈**: FastAPI + React + Vite + Docker

---

## 目录

1. [环境配置问题](#环境配置问题)
2. [API集成问题](#api集成问题)
3. [部署问题](#部署问题)
4. [前端开发问题](#前端开发问题)
5. [后端开发问题](#后端开发问题)
6. [Docker相关问题](#docker相关问题)
7. [性能优化问题](#性能优化问题)
8. [最佳实践](#最佳实践)

---

## 环境配置问题

### 问题 1.1: 后端无法启动 - .env 文件缺失

**现象**:
```bash
./run_dev.sh: ./backend/.env not found. Please create it first.
```

**原因**: 后端启动脚本强制要求 `backend/.env` 文件存在

**解决方案**:
```bash
# 复制示例配置文件
cp .env.example backend/.env

# 编辑并填入必需的 API 密钥
vim backend/.env
```

**预防措施**:
- 在项目 README 中明确说明配置步骤
- 将 `.env` 添加到 `.gitignore`
- 提供完整的 `.env.example` 模板

---

### 问题 1.2: API Key 格式错误

**现象**:
```
Authentication failed: Invalid API key format
```

**原因**: ModelScope API Key 格式应为 `ms-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

**解决方案**:

检查 `.env` 文件中的 API Key 格式:
```bash
# 正确的格式
MODELSCOPE_API_KEY=ms-a1b2c3d4-e5f6-7890-abcd-ef1234567890

# 错误的格式
MODELSCOPE_API_KEY=sk-a1b2c3d4e5f67890  # 这是 DashScope 的格式
```

**获取 API Key 的正确途径**:
- **DashScope**: https://help.aliyun.com/zh/model-studio/get-api-key (格式: `sk-xxxxx`)
- **ModelScope**: https://modelscope.cn/my/myaccesstoken (格式: `ms-xxxxx`)

---

### 问题 1.3: Redis 连接失败

**现象**:
```
Error connecting to Redis: Error 111 connecting to localhost:6379
```

**原因**: Redis 服务未启动或地址配置错误

**解决方案**:

1. 检查 Redis 是否运行:
```bash
redis-cli ping
# 应返回: PONG
```

2. 启动 Redis:
```bash
# Ubuntu/Debian
sudo systemctl start redis

# macOS
brew services start redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

3. 检查 `.env` 配置:
```bash
REDIS_URL=redis://localhost:6379/0
```

---

## API集成问题

### 问题 2.1: DashScope Wan2.6 模型调用失败

**现象**:
```
Model not found: wan2.6-t2v
```

**原因**:
- API Key 错误或未激活 DashScope 服务
- 模型名称拼写错误
- 区域不匹配

**解决方案**:

1. 验证 API Key:
```bash
cd backend
python -c "
from dashscope import VideoSynthesis
from src.config.settings import settings

rsp = VideoSynthesis.async_call(
    api_key=settings.dashscope_api_key,
    model='wan2.6-t2v',
    prompt='测试',
    size='1280*720',
    duration=5,
)
print(f'Task ID: {rsp.output.task_id}')
"
```

2. 检查模型名称: 必须是 `'wan2.6-t2v'` (注意小写和点号)

3. 确认 API Key 来源: 必须来自阿里云 DashScope,不是其他平台

**相关文档**: `docs/wan26-migration-summary.md`

---

### 问题 2.2: ModelScope LLM 调用超时

**现象**:
```
Timeout error: Request timed out after 30s
```

**原因**:
- 网络问题
- API 服务繁忙
- base_url 配置错误

**解决方案**:

1. 检查 base_url 配置:
```bash
# .env 文件
MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1
QWEN_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
```

2. 测试连接:
```bash
cd backend
python -c "
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from src.config.settings import settings

llm = ChatOpenAI(
    model=settings.qwen_model,
    api_key=settings.modelscope_api_key,
    base_url=settings.modelscope_base_url,
    timeout=60,  # 增加超时时间
)
response = llm.invoke([HumanMessage(content='你好')])
print(response.content)
"
```

3. 如果网络不稳定,可以在 `LLMOrchestrator` 中增加重试逻辑

**相关文件**: `backend/src/core/llm_orchestrator.py`

---

### 问题 2.3: Embedding 服务不可用

**现象**:
```
Template matching failed: Embedding service error
```

**原因**: ModelScope embedding API 配置错误或服务不可用

**解决方案**:

1. 检查 embedding 配置:
```python
# backend/src/core/template_router.py
embeddings = OpenAIEmbeddings(
    model="text-embedding-v2",
    api_key=settings.modelscope_api_key,
    base_url=settings.modelscope_base_url,
)
```

2. 如果 embedding 服务失败,会自动降级到关键词匹配:
```python
# TemplateRouter.match_template() 会自动回退
```

3. 验证 embedding 服务:
```bash
cd backend
python -c "
from langchain_openai import OpenAIEmbeddings
from src.config.settings import settings

embeddings = OpenAIEmbeddings(
    model='text-embedding-v2',
    api_key=settings.modelscope_api_key,
    base_url=settings.modelscope_base_url,
)
result = embeddings.embed_query('测试文本')
print(f'Embedding dimension: {len(result)}')
"
```

---

## 部署问题

### 问题 3.1: ModelScope Studio 部署 - API 路由错误

**现象**:
前端请求失败,控制台显示:
```
GET http://localhost:7860/v1/t2v/plan 404 (Not Found)
```

**原因**: ModelScope Studio 的资源路径带有 hash 前缀,API 路径需要相对计算

**解决方案**:

修改 `frontend/src/api/client.ts`:
```typescript
// 错误的做法
const API_BASE_URL = '/v1/t2v'

// 正确的做法 - 从资源 URL 推导
const assetUrl = new URL(import.meta.url)
const appBase = assetUrl.pathname.replace(/\/assets\/.*/, '')
const API_BASE_URL = `${appBase}/v1/t2v`
```

**提交记录**:
- `47925cf` - fix: handle dev and production API base URL differently
- `1a70d8f` - fix: derive API base URL from bundled asset URL

---

### 问题 3.2: ModelScope Studio 认证失败

**现象**:
```
401 Unauthorized
```

**原因**: 部署到 Studio 时需要在请求头中携带 token

**解决方案**:

在 `frontend/src/api/client.ts` 中添加:
```typescript
// 从 URL 参数提取 studio_token
const urlParams = new URLSearchParams(window.location.search)
const studioToken = urlParams.get('studio_token')

// 创建 axios 实例时添加请求头
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: studioToken ? {
    'X-Studio-Token': studioToken
  } : undefined
})
```

**提交记录**: `801f855` - feat: add ModelScope Studio token support

---

### 问题 3.3: Docker 部署 - 静态资源无法访问

**现象**:
前端页面显示,但视频和音频文件无法加载:
```
GET /static/vedios/... 404
```

**原因**: Nginx 配置未正确转发静态资源请求

**解决方案**:

检查 `docker/nginx.conf` 或 `docker/nginx.modelscope.conf`:
```nginx
location /static/ {
    alias /var/lib/prism/static/;
    autoindex off;

    # 添加日志
    access_log /dev/stdout;
    error_log /dev/stderr info;
}

location /api/v1/t2v/ {
    proxy_pass http://backend:8000/v1/t2v/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

**注意事项**:
- 静态资源目录拼写: `vedios` (不是 `videos`)
- 确保容器内 `/var/lib/prism/static` 目录存在且有权限
- 检查 `STATIC_ROOT` 环境变量配置

**提交记录**: `b252336` - fix: improve production deployment and UI polish

---

### 问题 3.4: Docker 构建失败 - VITE_BASE 未传递

**现象**:
前端构建后,API 请求路径错误

**原因**: Dockerfile 未传递 `VITE_BASE` 构建参数

**解决方案**:

在 `frontend/Dockerfile` 中:
```dockerfile
# 添加 ARG
ARG VITE_BASE=./
ENV VITE_BASE=${VITE_BASE}

# 构建时传递
RUN npm run build
```

在 `docker/docker-compose.yml` 中:
```yaml
services:
  frontend:
    build:
      context: ../frontend
      args:
        VITE_BASE: './'  # 或其他基础路径
```

**提交记录**: `0760454` - feat: add configurable VITE_BASE for flexible deployment

---

## 前端开发问题

### 问题 4.1: 开发环境 API 请求被 CORS 阻止

**现象**:
浏览器控制台显示:
```
Access to XMLHttpRequest at 'http://localhost:8000' from origin 'http://localhost:5173'
has been blocked by CORS policy
```

**原因**: Vite 开发服务器请求后端 API 被 CORS 策略阻止

**解决方案**:

在 `frontend/vite.config.ts` 中配置代理:
```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

在 `frontend/src/api/client.ts` 中:
```typescript
// 开发环境使用代理路径
const API_BASE_URL = '/api/v1/t2v'

// 生产环境使用相对路径
// const API_BASE_URL = './v1/t2v'
```

---

### 问题 4.2: UI 元素重叠 - z-index 问题

**现象**:
下载按钮被其他 UI 元素遮挡,无法点击

**原因**: CSS z-index 层级未正确设置

**解决方案**:

在 `frontend/src/components/VideoView.tsx` 中:
```tsx
{/* 下载按钮容器 */}
<div className="fixed bottom-4 right-4 z-20">
  <button>Download</button>
</div>

{/* 下拉菜单 */}
<div className="z-50">
  {/* menu items */}
</div>
```

**规则**:
- 导航栏/侧边栏: `z-10` 到 `z-20`
- 下拉菜单/模态框: `z-40` 到 `z-50`
- 通知/Toast: `z-50` 以上

**提交记录**: `07e3ebb` - fix: add z-index to download button and dropdown to prevent overlap

---

### 问题 4.3: 状态管理混乱 - 视频生成状态不更新

**现象**:
视频生成完成后,前端仍显示"处理中"状态

**原因**:
- 状态轮询逻辑错误
- 未正确处理后端返回的状态
- React 状态更新时机错误

**解决方案**:

1. 确保状态枚举一致性:
```typescript
// frontend/src/types/job.ts
export enum JobState {
  CREATED = 'CREATED',
  SUBMITTED = 'SUBMITTED',
  RUNNING = 'RUNNING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED'
}
```

2. 使用轮询 + WebSocket 双重机制:
```typescript
// 短轮询获取状态更新
useEffect(() => {
  if (job.state === JobState.RUNNING) {
    const interval = setInterval(async () => {
      const updated = await fetchJobStatus(jobId)
      setJob(updated)
    }, 2000)
    return () => clearInterval(interval)
  }
}, [jobId, job.state])
```

3. 添加超时保护:
```typescript
const TIMEOUT_MS = 300000 // 5分钟
const startTime = Date.now()

if (Date.now() - startTime > TIMEOUT_MS) {
  setError('Generation timeout')
}
```

---

## 后端开发问题

### 问题 5.1: FFmpeg 音视频拆分失败

**现象**:
```
FFmpeg error: Invalid data found when processing input
```

**原因**:
- 下载的视频文件损坏
- FFmpeg 命令参数错误
- 视频编码格式不支持

**解决方案**:

在 `backend/src/services/ffmpeg_splitter.py` 中:
```python
def split_video_audio(video_path: str) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    try:
        # 先验证文件
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # 获取视频信息
        probe = ffprobe(video_path)
        if not probe.get('streams'):
            raise ValueError("No video streams found")

        # 拆分视频
        video_output = video_path.replace('.mp4', '_video.mp4')
        audio_output = video_path.replace('.mp4', '_audio.mp3')

        # 使用 subprocess 调用 ffmpeg
        subprocess.run([
            'ffmpeg', '-i', video_path,
            '-an', '-c:v', 'copy', video_output,
            '-y'
        ], check=True, capture_output=True)

        subprocess.run([
            'ffmpeg', '-i', video_path,
            '-vn', '-c:a', 'mp3', audio_output,
            '-y'
        ], check=True, capture_output=True)

        return video_output, audio_output, probe.get('format', {}).get('duration')

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        # 回退:仅保留视频文件
        return video_path, None, None
    except Exception as e:
        logger.error(f"Split error: {e}")
        return None, None, None
```

**回退策略**: 如果音视频拆分失败,至少保留原始视频文件

**相关文件**: `backend/src/services/ffmpeg_splitter.py`

---

### 问题 5.2: RQ Worker 任务不执行

**现象**:
提交渲染请求后,任务状态一直是 `queued`,不执行

**原因**:
- RQ worker 未启动
- Redis 连接配置不一致
- 队列名称不匹配

**解决方案**:

1. 启动 RQ worker:
```bash
cd backend
./run_worker.sh
```

2. 检查 worker 配置:
```python
# backend/src/workers/render_worker.py
from redis import Redis
from rq import Worker, Queue

redis_conn = Redis.from_url(settings.redis_url)
queue = Queue(settings.rq_queue_name, connection=redis_conn)  # 默认 'prism'

with Worker([queue], connection=redis_conn):
    work()
```

3. 检查队列状态:
```bash
# 查看 RQ 队列
cd backend
python -c "
from redis import Redis
from rq import Queue
from src.config.settings import settings

q = Queue(settings.rq_queue_name, connection=Redis.from_url(settings.redis_url))
print(f'Pending jobs: {len(q)}')
print(f'Failed jobs: {len(q.failed_job_registry)}')
"
```

4. 环境变量配置:
```bash
# .env
RQ_QUEUE_NAME=prism  # 前后端必须一致
REDIS_URL=redis://localhost:6379/0
```

**相关文件**: `backend/run_worker.sh`, `backend/src/workers/render_worker.py`

---

### 问题 5.3: 数据库锁定 - SQLite 并发问题

**现象**:
```
sqlite3.OperationalError: database is locked
```

**原因**: SQLite 在高并发写入时会出现锁定问题

**解决方案**:

1. 使用 WAL 模式:
```python
# backend/src/models/database.py
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    isolation_level="DEFERRED"  # 延迟锁定
)

# 启用 WAL 模式
with engine.connect() as conn:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
```

2. 添加重试机制:
```python
from sqlalchemy import exc
import time

def execute_with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except exc.OperationalError as e:
            if "locked" in str(e) and attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
            else:
                raise
```

3. 生产环境建议使用 PostgreSQL:
```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost/prism
```

**相关文件**: `backend/src/models/database.py`

---

### 问题 5.4: 模板匹配失败 - 无合适模板

**现象**:
```
ValueError: No suitable template found for IR
```

**原因**:
- 模板库为空
- 语义相似度低于阈值
- 关键词匹配失败

**解决方案**:

1. 检查模板库:
```bash
cd backend
python -c "
from src.models.database import SessionLocal
from src.models.template import TemplateModel

db = SessionLocal()
templates = db.query(TemplateModel).all()
print(f'Total templates: {len(templates)}')
for t in templates:
    print(f'- {t.template_id} (v{t.version}): {t.tags}')
"
```

2. 降低匹配阈值:
```bash
# .env
TEMPLATE_MATCH_MIN_CONFIDENCE=0.3  # 默认 0.5
```

3. 添加默认兜底模板:
```python
# backend/src/core/template_router.py
def match_template(self, ir: IR) -> Optional[TemplateMatch]:
    match = self._semantic_match(ir)
    if not match:
        match = self._keyword_match(ir)
    if not match:
        # 使用通用模板兜底
        match = self._get_fallback_template()
    return match
```

**相关文件**: `backend/src/core/template_router.py`

**提交记录**: `47f2cec` - feat: Add default fallback template and general health template

---

## Docker相关问题

### 问题 6.1: Docker 容器内权限不足

**现象**:
```
PermissionError: [Errno 13] Permission denied: '/var/lib/prism/static'
```

**原因**: 容器内进程无写入权限

**解决方案**:

在 `Dockerfile` 中:
```dockerfile
# 创建目录并设置权限
RUN mkdir -p /var/lib/prism/static && \
    chown -R appuser:appuser /var/lib/prism

# 切换到非 root 用户
USER appuser
```

或使用回退路径:
```python
# backend/src/services/asset_storage.py
class AssetStorage:
    def _get_static_root(self) -> str:
        if os.access(settings.static_root, os.W_OK):
            return settings.static_root
        else:
            logger.warning(f"No write access to {settings.static_root}, using backend/data")
            os.makedirs('backend/data', exist_ok=True)
            return 'backend/data'
```

---

### 问题 6.2: Docker 镜像体积过大

**现象**:
构建的镜像超过 2GB,推送和拉取缓慢

**原因**: 包含不必要的依赖和文件

**解决方案**:

使用多阶段构建:
```dockerfile
# 构建阶段
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# 运行阶段
FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force
CMD ["npm", "run", "preview"]
```

优化 Python 镜像:
```dockerfile
FROM python:3.11-slim AS builder

# 只安装必需的依赖
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 运行时不包含构建工具
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
```

---

### 问题 6.3: Docker Compose 网络问题

**现象**:
```
Failed to connect to backend: Connection refused
```

**原因**: 容器间网络配置错误

**解决方案**:

在 `docker/docker-compose.yml` 中:
```yaml
services:
  backend:
    build: ../backend
    networks:
      - prism-net
    ports:
      - "8000:8000"

  frontend:
    build: ../frontend
    networks:
      - prism-net
    depends_on:
      - backend
    environment:
      - API_BASE_URL=http://backend:8000  # 使用服务名

  nginx:
    image: nginx:alpine
    networks:
      - prism-net
    ports:
      - "7860:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf

networks:
  prism-net:
    driver: bridge
```

**注意事项**:
- 容器间使用服务名 (如 `backend`) 而非 `localhost`
- 确保所有服务在同一网络中
- 检查防火墙是否阻止了端口映射

---

## 性能优化问题

### 问题 7.1: 视频生成慢 - 并发优化

**现象**:
生成多个镜头时串行执行,总耗时过长

**解决方案**:

使用并发生成:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def generate_shots_concurrent(shot_requests: List[ShotRequest]):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=3) as executor:  # 限制并发数
        tasks = [
            loop.run_in_executor(
                executor,
                generate_single_shot,
                shot_req
            )
            for shot_req in shot_requests
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

**配置并发限制**:
```bash
# .env
MAX_CONCURRENT_JOBS_PER_IP=5  # 全局限流
MAX_CONCURRENT_SHOTS_PER_JOB=3  # 单任务内并发
```

---

### 问题 7.2: 前端加载慢 - 代码分割

**现象**:
首次加载时间长,JavaScript 包体积大

**解决方案**:

使用路由级别的代码分割:
```typescript
// frontend/src/App.tsx
import { lazy, Suspense } from 'react'

const Workbench = lazy(() => import('./components/Workbench'))
const Sidebar = lazy(() => import('./components/Sidebar'))

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Workbench />
      <Sidebar />
    </Suspense>
  )
}
```

在 `vite.config.ts` 中:
```typescript
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['react', 'react-dom'],
          'ui': ['framer-motion', '@headlessui/react'],
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
})
```

---

### 问题 7.3: API 响应慢 - 缓存策略

**现象**:
重复请求相同内容,每次都重新计算

**解决方案**:

添加 Redis 缓存:
```python
from functools import wraps
import hashlib
import json

def cache_result(ttl=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = f"cache:{func.__name__}:{hash_args(args, kwargs)}"

            # 尝试从缓存获取
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            redis_client.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

# 使用
@cache_result(ttl=1800)  # 30分钟
def match_template(ir: IR) -> TemplateMatch:
    # ...
```

---

## 最佳实践

### 开发流程

1. **环境配置**
   - 始终从 `.env.example` 创建 `.env`
   - 使用 Docker Compose 统一开发环境
   - 在 README 中明确依赖版本

2. **API 集成**
   - 先在隔离环境测试 API 可用性
   - 添加详细的错误日志
   - 实现重试和降级机制

3. **部署流程**
   - 使用 CI/CD 自动化部署
   - 部署前在 staging 环境测试
   - 保留回滚方案

4. **监控与日志**
   - 使用结构化日志 (structlog)
   - 关键操作添加审计日志
   - 设置告警规则

### 代码质量

1. **错误处理**
   - 永远不吞掉异常
   - 提供有意义的错误信息
   - 实现全局异常处理器

2. **类型安全**
   - 使用 Pydantic 验证输入
   - TypeScript 前端类型定义
   - 避免使用 `Any` 类型

3. **测试覆盖**
   - 单元测试覆盖核心逻辑
   - 集成测试验证 API
   - E2E 测试关键流程

### 安全建议

1. **敏感信息**
   - 永远不提交 API Key 到代码库
   - 使用环境变量管理密钥
   - 轮换定期更换密钥

2. **访问控制**
   - 实施速率限制
   - 添加身份认证
   - 验证输入合法性

3. **数据保护**
   - PII 数据脱敏
   - 加密敏感数据
   - 实施数据保留策略

---

## 常用命令速查

### 本地开发

```bash
# 后端
cd backend
./run_dev.sh          # 启动开发服务器
./run_worker.sh       # 启动 RQ worker

# 前端
cd frontend
npm run dev           # 启动 Vite 开发服务器
npm run build         # 构建生产版本

# 测试
cd backend
pytest tests/         # 运行测试
```

### Docker 部署

```bash
# 构建并启动
cd docker
docker-compose up --build

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 进入容器
docker-compose exec backend bash
docker-compose exec frontend sh

# 清理
docker-compose down -v  # 删除卷
```

### 调试

```bash
# 检查 Redis
redis-cli
> keys prism:*
> get prism:job:123

# 检查数据库
sqlite3 backend/data/jobs.db
> SELECT * FROM jobs WHERE state='FAILED';

# 检查 RQ 队列
cd backend
python -m rq info --url redis://localhost:6379/0
```

---

## 相关文档

- [README.md](../README.md) - 项目总览
- [wan26-migration-summary.md](./wan26-migration-summary.md) - Wan2.6 集成说明
- [api.md](./api.md) - API 文档
- [PIPELINE.md](./PIPELINE.md) - 处理流程
- [backend-dataflow.md](./backend-dataflow.md) - 后端数据流

---

## 贡献

如果遇到新问题或有更好的解决方案,请提交 PR 更新本文档。

---

**维护者**: Prism 开发团队
**许可证**: 项目内部使用
