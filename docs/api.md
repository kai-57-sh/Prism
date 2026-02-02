# Prism 后端 API 文档（当前实现）

本文档以 `backend/src` 代码为准，聚焦前端对接所需的接口、字段、状态与错误格式。

## 1. 基本信息

- **服务名称**：Prism Medical Text-to-Video Agent API
- **认证**：无（公共 API）
- **内容类型**：`application/json`
- **接口前缀**：`/v1/t2v`
- **Swagger**：`http://<backend_host>:8000/docs`（直连后端可用）
- **Redoc**：`http://<backend_host>:8000/redoc`
- **根路径**：`GET /`
- **健康检查**：`GET /health`
- **静态资源**：`/static/*`（后端挂载，`/var/lib/prism/static`，无权限时回退到 `backend/data`）

### 常用 Base URL

- 本地开发（直连后端）：`http://localhost:8000`
- React Web UI（Vite dev 代理）：`http://localhost:5173`（前端请求走 `/api` 前缀）
- Docker Compose（Nginx 反代）：`http://localhost:7860`
  - 转发 `/v1/t2v/`、`/api/`、`/static/`。

## 2. 推荐对接流程

### 2.1 推荐流程（Plan → Render）

1. `POST /v1/t2v/plan` 生成脚本与分镜（不渲染视频）
2. 轮询 `GET /v1/t2v/jobs/{job_id}`，拿到 `script` 与 `shot_plan`
3. 可选：`PATCH /v1/t2v/jobs/{job_id}/shots/{shot_id}` 调整文案/画面
4. `POST /v1/t2v/jobs/{job_id}/render` 入队渲染（需要 RQ worker）
5. 轮询 `GET /v1/t2v/jobs/{job_id}` 获取 `assets`

### 2.2 直接生成（Generate）

- `POST /v1/t2v/generate` 会在请求内执行完整流程并返回 **202**，但实际在生成完成后才返回。
- 适合调试，不适合长时任务的生产场景。

### 2.3 迭代与修订

- `POST /v1/t2v/jobs/{job_id}/revise`：基于已成功任务进行修订，创建新任务。

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
      "message": "Job must be in SUCCEEDED state to revise, current state: RUNNING"
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

- `VALIDATION_ERROR`：请求字段非法、模板匹配失败、限流等
- `CLARIFICATION_REQUIRED`：需要补充澄清信息
- `INVALID_VALUE`：ValueError（由全局异常处理器抛出）
- `JOB_NOT_FOUND`：任务不存在
- `SHOT_NOT_FOUND`：指定分镜不存在
- `INVALID_JOB_STATE`：任务状态不允许当前操作
- `INVALID_REFINEMENT`：反馈文本无法解析或不满足约束
- `NO_PREVIEW_ASSETS` / `INVALID_SEEDS`：finalize 相关校验失败
- `RENDER_ERROR` / `PLANNING_ERROR` / `GENERATION_ERROR` / `REVISION_ERROR` / `FINALIZATION_ERROR`
- `REGENERATE_FAILED`
- `INTERNAL_ERROR`

## 4. 任务状态（Job State）

`status` 取值：

- `CREATED`
- `SUBMITTED`
- `RUNNING`
- `SUCCEEDED`
- `FAILED`

说明：
- `RUNNING` 时可能已有部分 `shot_assets`（后端会增量写入）
- `SUCCEEDED` 时可以读取完整 `assets` / `shot_assets`

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

> 注：若 ffmpeg 不可用，`audio_url` 可能为空。

### 5.2 ShotPlan（前端简化版）

```json
{
  "shots": [
    {
      "shot_id": 1,
      "visual_prompt": "...",
      "narration": "...",
      "duration": 4
    }
  ]
}
```

### 5.3 JobStatusResponse（GET /v1/t2v/jobs/{job_id}）

- `job_id`: string
- `status`: string
- `created_at` / `updated_at`: ISO8601
- `template_id`: string
- `quality_mode`: `fast` | `balanced` | `high`
- `resolution`: string（RUNNING/SUCCEEDED）
- `total_duration_s`: number（SUCCEEDED）
- `shot_assets`: ShotAsset[]（可能包含每个镜头的多个候选）
- `assets`: ShotAsset[]（每个镜头仅一个主候选，供前端直接使用）
- `preview_shot_assets`: ShotAsset[]（当前版本未写入，通常为空）
- `script`: string（由 `shot_plan` 组合生成）
- `shot_plan`: ShotPlan
- `error_details` / `error`: object（FAILED）

## 6. 接口列表

**curl 示例约定**：
```bash
BASE_URL=http://localhost:8000
JOB_ID=550e8400-e29b-41d4-a716-446655440000
```

### 6.1 GET /health

**描述**：健康检查

```bash
curl -s "$BASE_URL/health"
```

### 6.2 GET /

**描述**：根信息

```bash
curl -s "$BASE_URL/"
```

### 6.3 POST /v1/t2v/plan

**描述**：生成脚本与分镜（不渲染）

**请求体**（与 generate 相同）：
```json
{
  "user_prompt": "create an insomnia emotion video, late night bedroom",
  "quality_mode": "balanced",
  "duration_preference_s": 9,
  "resolution": "1280x720"
}
```

**响应（202）**：
```json
{
  "job_id": "...",
  "status": "CREATED",
  "message": "Plan created successfully. Use GET /v1/t2v/jobs/{job_id} to review."
}
```

### 6.4 POST /v1/t2v/generate

**描述**：直接生成（同步等待完成，仍返回 202）

请求/响应结构同 `plan`。

> 备注：`duration_preference_s` 仅做校验，实际时长由 LLM + 模板决定。

### 6.5 POST /v1/t2v/jobs/{job_id}/render

**描述**：将已规划任务加入 RQ 队列渲染（异步）

**响应（202）**：
```json
{
  "job_id": "...",
  "status": "SUBMITTED",
  "message": "Generation queued. Use GET /v1/t2v/jobs/{job_id} to track progress."
}
```

**校验要点**：
- 任务必须存在且未运行
- 必须有 `shot_requests` 且尚未生成 `shot_assets`

### 6.6 GET /v1/t2v/jobs/{job_id}

**描述**：查询任务状态

```bash
curl -s "$BASE_URL/v1/t2v/jobs/$JOB_ID"
```

### 6.7 PATCH /v1/t2v/jobs/{job_id}/shots/{shot_id}

**描述**：更新单个镜头的文案/画面

**请求体**：
```json
{
  "visual_prompt": "...",
  "narration": "..."
}
```

**响应**：返回更新后的 shot

### 6.8 POST /v1/t2v/jobs/{job_id}/shots/{shot_id}/regenerate

**描述**：重生成单个镜头（必须 `SUCCEEDED`）

**请求体**（可选）：
```json
{
  "visual_prompt": "...",
  "narration": "..."
}
```

**响应**：
```json
{
  "shot_id": 1,
  "asset": { /* ShotAsset */ },
  "message": "shot_regenerated"
}
```

### 6.9 POST /v1/t2v/jobs/{job_id}/revise

**描述**：修订（生成新任务）

**请求体**：
```json
{ "feedback": "less camera shake, shorter narration" }
```

**响应（202）**：
```json
{
  "job_id": "...",
  "parent_job_id": "...",
  "status": "CREATED",
  "message": "Revision job created. Use GET /v1/t2v/jobs/{job_id} to track progress.",
  "targeted_fields": ["camera", "narration"]
}
```

### 6.10 POST /v1/t2v/jobs/{job_id}/finalize

**描述**：按选定 seed 生成 1080P 成片

**请求体**：
```json
{
  "selected_seeds": {
    "1": 12345,
    "2": 67890
  }
}
```

**注意**：当前版本未写入 `preview_shot_assets`，若为空会返回 `NO_PREVIEW_ASSETS`。

## 7. 限流与并发限制

- `RATE_LIMIT_PER_MIN = 10`
- `MAX_CONCURRENT_JOBS_PER_IP = 5`

触发限制时返回 **400 + VALIDATION_ERROR**。

## 8. 静态资源访问

- 静态前缀：`/static`
- 子目录：`vedios/`、`audio/`、`metadata/`（注意拼写 `vedios`）
- 默认目录：`/var/lib/prism/static`，无权限时回退到 `backend/data`

## 9. OpenAPI 差异（当前实现）

- 错误响应格式与 OpenAPI 不完全一致。
- `POST /v1/t2v/plan`、`/render`、`/shots/*` 在 OpenAPI 中可能缺失。
- `preview_shot_assets` 在模型中存在，但当前实现未写入。

## 10. OpenAPI 规格文件位置

- `specs/001-medical-t2v-agent/contracts/openapi.yaml`

如需补充字段或对齐 OpenAPI，请注明期望行为，我们可以同步调整后端与文档。
