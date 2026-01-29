# Wan2.6-t2v 和 Qwen3-235B 集成说明

## 架构概述

本系统使用两个不同的 API 服务：

1. **Wan2.6-t2v (DashScope/阿里云)** - 文本生成视频模型
2. **Qwen3-235B-A22B-Instruct-2507 (ModelScope/魔搭社区)** - 大语言模型

## API 使用说明

### 1. Wan2.6-t2v 视频生成

**服务提供商**: 阿里云 DashScope
**API 调用示例**: `docs/reference-pre/wan2.6.py`

```python
from dashscope import VideoSynthesis

# 提交异步任务
rsp = VideoSynthesis.async_call(
    api_key=settings.dashscope_api_key,
    model='wan2.6-t2v',
    prompt='...',
    size='1280*720',
    duration=10,
    seed=12345,
    prompt_extend=True,
    watermark=False,
)

# 等待任务完成
rsp = VideoSynthesis.wait(task=rsp, api_key=settings.dashscope_api_key)
video_url = rsp.output.video_url
```

**相关文件**:
- `backend/src/core/wan26_adapter.py` - Wan2.6 适配器

**环境变量**:
- `DASHSCOPE_API_KEY` - 阿里云 DashScope API Key
- 获取地址: https://help.aliyun.com/zh/model-studio/get-api-key

---

### 2. Qwen3-235B-A22B-Instruct-2507 语言模型

**服务提供商**: 魔搭社区 ModelScope
**API 调用示例**: `docs/reference-pre/Qwen3-235B-A22B-Instruct-2507.py`

```python
from openai import OpenAI

client = OpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    api_key='ms-your_token_here',
)

response = client.chat.completions.create(
    model='Qwen/Qwen3-235B-A22B-Instruct-2507',
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': '你好'}
    ],
    stream=True
)

for chunk in response:
    if chunk.choices:
        print(chunk.choices[0].delta.content, end='', flush=True)
```

**相关文件**:
- `backend/src/core/llm_orchestrator.py` - LLM 编排器（IR 解析和模板实例化）
- `backend/src/core/input_processor.py` - 输入处理器（语言检测、翻译）
- `backend/src/core/template_router.py` - 模板路由器（语义搜索）

**环境变量**:
- `MODELSCOPE_API_KEY` - 魔搭社区 API Token
- `MODELSCOPE_BASE_URL` - ModelScope API 端点（默认: `https://api-inference.modelscope.cn/v1`）
- `QWEN_MODEL` - 模型 ID（默认: `Qwen/Qwen3-235B-A22B-Instruct-2507`）
- 获取地址: https://modelscope.cn/my/myaccesstoken

---

## 集成实现

### LLM 集成（使用 LangChain + OpenAI SDK）

通过 LangChain 的 `ChatOpenAI` 类调用 ModelScope 的 OpenAI 兼容接口：

```python
from langchain_openai import ChatOpenAI
from src.config.settings import settings

llm = ChatOpenAI(
    model=settings.qwen_model,
    api_key=settings.modelscope_api_key,
    base_url=settings.modelscope_base_url,
    temperature=0.0,
)

# 使用 LangChain 消息格式
from langchain.schema import HumanMessage, SystemMessage

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="你好"),
]
response = llm.invoke(messages)
```

### Embeddings 集成

使用 LangChain 的 `OpenAIEmbeddings` 调用 ModelScope 的 embedding 服务：

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-v2",
    api_key=settings.modelscope_api_key,
    base_url=settings.modelscope_base_url,
)
```

---

## 环境配置

### `.env` 文件配置

```bash
# DashScope API Key (阿里云) - 用于 Wan2.6-t2v 视频生成
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# ModelScope API Key (魔搭社区) - 用于 Qwen3-235B 语言模型
MODELSCOPE_API_KEY=ms-your_modelscope_token_here

# ModelScope API Base URL (使用 OpenAI 兼容接口)
MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1

# LLM Model Configuration (ModelScope model ID)
QWEN_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507

# 其他配置...
DATABASE_URL=sqlite:///./data/jobs.db
REDIS_URL=redis://localhost:6379/0
STATIC_ROOT=/var/lib/prism/static
LOG_LEVEL=INFO
```

---

## 依赖项

### `requirements.txt`

```txt
# LangChain 和 LLM
langchain==0.1.0
langchain-openai==0.0.2
langchain-community==0.0.10

# DashScope SDK (for Wan2.6-t2v)
dashscope==1.17.0

# OpenAI SDK (for ModelScope OpenAI-compatible endpoint)
openai>=1.0.0

# 其他依赖...
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.2
pydantic-settings==2.1.0
sqlalchemy==2.0.23
redis==5.0.1
faiss-cpu==1.7.4
```

---

## 配置文件

### `backend/src/config/settings.py`

```python
class Settings(BaseSettings):
    """应用配置"""

    # DashScope API Key for Wan2.6-t2v video generation
    dashscope_api_key: str = Field(default="", env="DASHSCOPE_API_KEY")

    # ModelScope API Key for Qwen LLM
    modelscope_api_key: str = Field(default="", env="MODELSCOPE_API_KEY")

    # ModelScope API endpoint
    modelscope_base_url: str = Field(
        default="https://api-inference.modelscope.cn/v1",
        env="MODELSCOPE_BASE_URL"
    )

    # LLM Model (ModelScope model ID)
    qwen_model: str = Field(
        default="Qwen/Qwen3-235B-A22B-Instruct-2507",
        env="QWEN_MODEL"
    )
```

---

## 工作流程

### 视频生成流程

1. **用户输入处理** (`InputProcessor`)
   - PII 脱敏
   - 语言检测
   - 可选翻译

2. **IR 解析** (`LLMOrchestrator.parse_ir`)
   - 使用 Qwen3-235B 解析用户意图
   - 生成中间表示（IR）

3. **模板匹配** (`TemplateRouter.match_template`)
   - 使用 Embeddings 进行语义搜索
   - 选择最佳模板

4. **模板实例化** (`LLMOrchestrator.instantiate_template`)
   - 使用 Qwen3-235B 填充模板
   - 生成详细的镜头计划

5. **视频生成** (`Wan26Adapter`)
   - 为每个镜头调用 Wan2.6-t2v
   - 使用 DashScope SDK

6. **视频合成** (`VideoComposer`)
   - 使用 FFmpeg 合成最终视频

---

## API 密钥获取

### DashScope API Key (阿里云)

1. 访问: https://help.aliyun.com/zh/model-studio/get-api-key
2. 登录阿里云账号
3. 创建 API Key
4. 设置环境变量 `DASHSCOPE_API_KEY`

### ModelScope API Key (魔搭社区)

1. 访问: https://modelscope.cn/my/myaccesstoken
2. 登录魔搭社区账号
3. 生成 Access Token
4. Token 格式: `ms-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
5. 设置环境变量 `MODELSCOPE_API_KEY`

---

## 测试

### 测试 Wan2.6-t2v

```bash
cd backend
python -c "
from dashscope import VideoSynthesis
from src.config.settings import settings

rsp = VideoSynthesis.async_call(
    api_key=settings.dashscope_api_key,
    model='wan2.6-t2v',
    prompt='一只可爱的小猫',
    size='1280*720',
    duration=5,
)
print(f'Task ID: {rsp.output.task_id}')
"
```

### 测试 Qwen3-235B

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
)
response = llm.invoke([HumanMessage(content='你好')])
print(response.content)
"
```

---

## 故障排查

### DashScope 相关问题

**问题**: `Invalid API key`
- 检查 `DASHSCOPE_API_KEY` 是否正确
- 确认 API Key 来自阿里云 DashScope

**问题**: `Model not found`
- 确认模型名称为 `wan2.6-t2v`
- 检查 DashScope 服务区域

### ModelScope 相关问题

**问题**: `Authentication failed`
- 检查 `MODELSCOPE_API_KEY` 格式应为 `ms-xxxxx`
- 确认 Token 来自魔搭社区

**问题**: `Model not found`
- 检查模型 ID: `Qwen/Qwen3-235B-A22B-Instruct-2507`
- 确认 base_url: `https://api-inference.modelscope.cn/v1`

---

## 参考文档

- Wan2.6-t2v API 示例: `docs/reference-pre/wan2.6.py`
- Qwen3-235B API 示例: `docs/reference-pre/Qwen3-235B-A22B-Instruct-2507.py`
- DashScope 文档: https://help.aliyun.com/zh/model-studio
- ModelScope 文档: https://modelscope.cn/docs
