# Prism 后端 API 文档（前端对接版）

本文档以当前后端实现为准，整理前端对接最关键的接口、字段、状态与错误格式。若与 OpenAPI 或其他说明不一致，请以本文件和后端代码为准。

## 1. 基本信息

- **服务名称**：Prism Medical Text-to-Video Agent API
- **认证**：无（公共 API）
- **内容类型**：`application/json`
- **接口前缀**：`/v1/t2v`
- **Swagger**：`http://<backend_host>:8000/docs`（仅直连后端可用）
- **Redoc**：`http://<backend_host>:8000/redoc`
- **根路径**：`GET /`
- **健康检查**：`GET /health`
- **静态资源**：`/static/*` → `backend/data/*`（后端已挂载，无需 Nginx）

### 常用 Base URL

- 本地开发（直连后端）：`http://localhost:8000`
- Docker Compose（前端容器内调用后端）：`http://backend:8000`
- Nginx 反代（当前 `docker/nginx.conf`）：`http://localhost:80`
  - 仅转发 `/v1/t2v/` 与 `/static/`，**不**转发 `/docs`。
  - README/集成文档中出现的 `/api` 前缀可能已过期，请以 Nginx 配置为准。

## 2. 对接流程（推荐）

1. `POST /v1/t2v/generate` 创建任务，获取 `job_id`
2. 轮询 `GET /v1/t2v/jobs/{job_id}` 直到 `status=SUCCEEDED` 或 `FAILED`
3. 若返回 `preview_shot_assets`，可调用 `POST /v1/t2v/jobs/{job_id}/finalize` 生成 1080P 成片，再继续轮询
4. 若需要迭代优化，调用 `POST /v1/t2v/jobs/{job_id}/revise` 创建新任务

## 3. 请求与响应通用规则

### 3.1 请求头

- `Content-Type: application/json`
- 无鉴权头

### 3.2 错误返回格式（务必兼容两种结构）

1) **请求参数校验失败（RequestValidationError）**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "loc": ["body", "resolution"],
        "msg": "resolution must be 1280x720 or 1920x1080",
        "type": "value_error"
      }
    ]
  }
}
```

2) **业务错误（HTTPException）**

```json
{
  "detail": {
    "error": {
      "code": "INVALID_JOB_STATE",
      "message": "Job must be in SUCCEEDED state to finalize, current state: RUNNING"
    }
  }
}
```

3) **需要澄清（HTTPException，字段可能为空）**

```json
{
  "detail": {
    "error": {
      "code": "CLARIFICATION_REQUIRED",
      "message": "No matching template found. Please provide more details."
    },
    "clarification_required_fields": []
  }
}
```

**前端解析建议**：
- 优先读取 `detail.error`
- 否则读取顶层 `error`

### 3.3 常见错误码

- `VALIDATION_ERROR`：请求字段非法（质量档位、分辨率、参数范围、限流等）
- `CLARIFICATION_REQUIRED`：需要补充澄清信息（字段列表可能为空）
- `INVALID_VALUE`：服务端 ValueError（较少出现，结构为顶层 `error`）
- `INVALID_JOB_STATE`：作业状态不允许当前操作
- `NO_PREVIEW_ASSETS`：未生成预览资源，无法 finalize
- `INVALID_SEEDS`：finalize 提交的 seed 与预览资源不匹配
- `INVALID_REFINEMENT`：反馈文本无法解析或不满足约束
- `JOB_NOT_FOUND`：任务不存在
- `GENERATION_ERROR` / `FINALIZATION_ERROR` / `REVISION_ERROR`：流程异常
- `INTERNAL_ERROR`：未捕获的服务错误

## 4. 任务状态（Job State）

`status` 取值：

- `CREATED`
- `SUBMITTED`
- `RUNNING`
- `SUCCEEDED`
- `FAILED`

前端建议：
- `SUCCEEDED`：展示预览/成品素材
- `FAILED`：展示 `error_details`
- 其他状态：继续轮询

## 5. 数据结构

### 5.1 ShotAsset

```json
{
  "shot_id": 1,
  "seed": 12345,
  "video_url": "/static/vedios/2026/01/28/<job>_shot_1.mp4",
  "audio_url": "/static/audio/2026/01/28/<job>_shot_1.mp3",
  "duration_s": 4,
  "resolution": "1280x720"
}
```

### 5.2 JobStatusResponse（GET /v1/t2v/jobs/{job_id}）

- `job_id`: string
- `status`: string（见上文）
- `created_at` / `updated_at`: ISO8601
- `template_id`: string
- `quality_mode`: `fast` | `balanced` | `high`
- `resolution`: string，仅在 `SUCCEEDED` 后可用
- `total_duration_s`: number，仅在 `SUCCEEDED` 后可用
- `shot_assets`: ShotAsset[]，仅在 `SUCCEEDED` 后可用
- `preview_shot_assets`: ShotAsset[]，仅在 `SUCCEEDED` 且有预览候选时可用
- `error_details`: object，仅在 `FAILED` 且有错误时可用

`error_details` 示例：

```json
{
  "code": "DASHSCOPE_RATE_LIMIT",
  "message": "Rate limit exceeded for video generation service",
  "classification": "retryable",
  "retryable": true,
  "suggested_modifications": ["Wait a few minutes and try again"]
}
```

> 注意：字段随错误类型变化，前端需做容错处理。

## 6. 接口列表

**curl 示例约定**：
```bash
BASE_URL=http://localhost:8000
JOB_ID=550e8400-e29b-41d4-a716-446655440000
```

### 6.1 GET /health

**描述**：健康检查

**curl 示例**：
```bash
curl -s "$BASE_URL/health"
```

**响应示例**：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "prism-backend"
}
```

**错误示例（服务异常时）**：
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred"
  }
}
```

### 6.2 GET /

**描述**：根信息

**curl 示例**：
```bash
curl -s "$BASE_URL/"
```

**响应示例**：
```json
{
  "name": "Prism Medical Text-to-Video Agent API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

**错误示例（服务异常时）**：
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred"
  }
}
```

### 6.3 POST /v1/t2v/generate

**描述**：提交文本生成请求

**请求体**：
```json
{
  "user_prompt": "create an insomnia emotion video, late night bedroom, low calm narration, no subtitles",
  "quality_mode": "balanced",
  "duration_preference_s": 9,
  "resolution": "1280x720"
}
```

**字段说明**：

- `user_prompt`（必填）：用户描述
- `quality_mode`（可选）：`fast` | `balanced` | `high`，默认 `balanced`
- `duration_preference_s`（可选）：2~15 秒（当前版本后端未使用，仅做校验）
- `resolution`（可选）：`1280x720` 或 `1920x1080`，默认 `1280x720`
  - 也接受 `1280*720` / `1920*1080`，会自动转为 `x`
- **不支持字段**：`audio_url` / `audio_file` / `audio_upload`（填了会报错）

**响应（202）**：
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "CREATED",
  "message": "Job submitted successfully. Use GET /v1/t2v/jobs/{job_id} to check status."
}
```

**curl 示例**：
```bash
curl -s "$BASE_URL/v1/t2v/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_prompt": "create an insomnia emotion video, late night bedroom, low calm narration, no subtitles",
    "quality_mode": "balanced",
    "duration_preference_s": 9,
    "resolution": "1280x720"
  }'
```

**错误示例（参数校验失败）**：
```bash
curl -s "$BASE_URL/v1/t2v/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_prompt": "create an insomnia emotion video",
    "resolution": "999x999"
  }'
```

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "loc": ["body", "resolution"],
        "msg": "resolution must be 1280x720 or 1920x1080",
        "type": "value_error"
      }
    ]
  }
}
```

**可能的错误**：
- 400 `VALIDATION_ERROR`（参数非法、模板匹配失败、限流等）
- 400 `CLARIFICATION_REQUIRED`（需要澄清）
- 500 `GENERATION_ERROR`

> 备注：当前实现会等待生成完成后返回，但仍使用 202 状态码。前端请始终以轮询 `GET /v1/t2v/jobs/{job_id}` 为准。

### 6.4 GET /v1/t2v/jobs/{job_id}

**描述**：查询任务状态

**响应（200）**：`JobStatusResponse`

**curl 示例**：
```bash
curl -s "$BASE_URL/v1/t2v/jobs/$JOB_ID"
```

**错误示例（任务不存在）**：
```bash
curl -s "$BASE_URL/v1/t2v/jobs/00000000-0000-0000-0000-000000000000"
```

```json
{
  "detail": {
    "error": {
      "code": "JOB_NOT_FOUND",
      "message": "Job 00000000-0000-0000-0000-000000000000 not found"
    }
  }
}
```

**错误**：
- 404 `JOB_NOT_FOUND`
- 500 `INTERNAL_ERROR`

### 6.5 POST /v1/t2v/jobs/{job_id}/finalize

**描述**：从预览候选中选择 seed，生成 1080P 最终成片（同一 `job_id` 会进入 RUNNING 并最终更新为 SUCCEEDED）

**请求体**：
```json
{
  "selected_seeds": {
    "1": 12345,
    "2": 67890
  }
}
```

**校验规则**：
- 仅当原任务 `status=SUCCEEDED`
- 必须存在 `preview_shot_assets`
- `selected_seeds` 必须与 preview 中的 `shot_id` 和 `seed` 匹配

**响应（202）**：
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "RUNNING",
  "message": "Finalization started. Use GET /v1/t2v/jobs/{job_id} to track progress.",
  "resolution": "1920x1080"
}
```

**curl 示例**：
```bash
curl -s "$BASE_URL/v1/t2v/jobs/$JOB_ID/finalize" \
  -H "Content-Type: application/json" \
  -d '{
    "selected_seeds": {
      "1": 12345,
      "2": 67890
    }
  }'
```

**错误示例（状态不允许 finalize）**：
```bash
curl -s "$BASE_URL/v1/t2v/jobs/$JOB_ID/finalize" \
  -H "Content-Type: application/json" \
  -d '{
    "selected_seeds": {
      "1": 12345
    }
  }'
```

```json
{
  "detail": {
    "error": {
      "code": "INVALID_JOB_STATE",
      "message": "Job must be in SUCCEEDED state to finalize, current state: RUNNING"
    }
  }
}
```

**可能的错误**：
- 400 `INVALID_JOB_STATE`
- 400 `NO_PREVIEW_ASSETS`
- 400 `INVALID_SEEDS`
- 404 `JOB_NOT_FOUND`
- 500 `FINALIZATION_ERROR`

### 6.6 POST /v1/t2v/jobs/{job_id}/revise

**描述**：根据反馈进行迭代优化，生成新任务

**请求体**：
```json
{
  "feedback": "less camera shake, shorter narration"
}
```

**约束**：`feedback` 长度 5~500

**响应（202）**：
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440001",
  "parent_job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "CREATED",
  "message": "Revision job created. Use GET /v1/t2v/jobs/{job_id} to track progress.",
  "targeted_fields": ["camera", "narration"]
}
```

**curl 示例**：
```bash
curl -s "$BASE_URL/v1/t2v/jobs/$JOB_ID/revise" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback": "less camera shake, shorter narration"
  }'
```

**错误示例（参数校验失败）**：
```bash
curl -s "$BASE_URL/v1/t2v/jobs/$JOB_ID/revise" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback": "no"
  }'
```

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "loc": ["body", "feedback"],
        "msg": "String should have at least 5 characters",
        "type": "string_too_short"
      }
    ]
  }
}
```

**可能的错误**：
- 400 `INVALID_JOB_STATE`
- 400 `INVALID_REFINEMENT`
- 404 `JOB_NOT_FOUND`
- 500 `REVISION_ERROR`

## 7. 限流与并发限制（当前实现）

后端在生成流程中做了基于 IP 的限流与并发控制：

- **每分钟请求数**：`RATE_LIMIT_PER_MIN = 10`
- **窗口**：60 秒
- **并发任务上限**：`MAX_CONCURRENT_JOBS_PER_IP = 5`

触发限制时返回 **400 + VALIDATION_ERROR**（非 429）。

## 8. 资产与静态资源访问

- `video_url` / `audio_url` 为相对路径（默认 `/static/...`）。
- 后端已挂载静态目录：`/static/*` → `backend/data/*`，直连后端即可访问。
- 目录结构如下（统一为 `vedios`）：
```
backend/data/vedios/YYYY/MM/DD/*.mp4
backend/data/audio/YYYY/MM/DD/*.mp3
backend/data/metadata/*.json
backend/data/jobs.db
```
- Nginx 反代时可直接转发 `/static/*` 到后端或挂载同一目录。

## 9. OpenAPI 差异（基于当前实现）

- 缺少 `/health` 与 `/`，以及静态资源挂载 `/static/*` 的说明。
- 错误响应格式不一致：OpenAPI 使用 `{"error": "string"}`，实际为 `{"error": {code, message, details}}` 或 `{"detail": {"error": {code, message}}}`。
- `POST /v1/t2v/generate` 实际返回 `202`（无 `201`），并支持 `resolution`；OpenAPI 未包含该字段。
- 速率限制与并发限制实际返回 `400 + VALIDATION_ERROR`，无 `429` 与 `Retry-After`；且只在生成流程中生效。
- `GET /v1/t2v/jobs/{job_id}` 实际包含 `preview_shot_assets`，OpenAPI 缺失；`video_url`/`audio_url` 为相对路径。
- `POST /v1/t2v/jobs/{job_id}/finalize` 实际仅返回任务状态，成片需通过 `GET /v1/t2v/jobs/{job_id}` 获取。
- `POST /v1/t2v/jobs/{job_id}/revise` 实际返回 `202 + ReviseResponse`，OpenAPI 有重复路径且返回码/结构不一致。
- `GenerateRequest.user_prompt` 的最小长度约束在实际实现中未强制。

## 10. OpenAPI 规格文件位置

- `specs/001-medical-t2v-agent/contracts/openapi.yaml`

> 注意：该文件包含部分与当前实现不一致的描述，前端对接以实际返回为准。

如需补充字段或对齐 OpenAPI，请注明期望表现，我们可以同步调整后端与文档。
