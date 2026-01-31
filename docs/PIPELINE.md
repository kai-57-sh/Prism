# 后端数据管道（Prompt -> Video + Audio + Metadata）

1. 请求接入与输入预处理
   - 入口：`POST /v1/t2v/generate`（`GenerationRequest`：`user_prompt`、`quality_mode`、`duration_preference_s`、`resolution`）。
   - `InputProcessor.process_input` 产出 `processed` 字典：`redacted_text`、`input_hash`、`pii_flags`、`detected_language`、`aligned_text`/`aligned_translation`。
   - `LLMOrchestrator.parse_ir` 输出 IR（`IR` Pydantic）：`topic`、`intent`、`style`、`scene`、`characters`、`emotion_curve`、`subtitle_policy`、`audio`、`duration_preference_s`、`quality_mode`。IR 最终以 `dict` 形式写入 `JobModel.ir`。

2. 模板匹配、镜头计划与请求编译
   - `TemplateRouter.match_template` 产出 `TemplateMatch`：`template_id`、`version`、`confidence`、`confidence_components`、`template`。
   - `LLMOrchestrator.instantiate_template` 产出 `ShotPlan`：`template_id`、`template_version`、`duration_s`、`subtitle_policy`、`shots[]`、`global_style`；随后 `_normalize_shot_plan` 统一 `shot_id`/`duration_s`。
   - `Validator.validate_parameters` 校验时长、分辨率、quality 模式限制等。
   - `PromptCompiler.compile_shot_prompt` 生成 `shot_requests[]`，每项结构：`{shot_id, compiled_prompt, compiled_negative_prompt, params{size,duration,seed,prompt_extend,watermark}}`。
   - `JobDB.create_job` 持久化核心中间态：`user_input_redacted`、`ir`、`shot_plan`、`shot_requests`、`quality_mode`、`resolution`、`state_transitions` 等，状态迁移：`CREATED -> SUBMITTED -> RUNNING`。

3. 分镜生成、资产落盘与元数据输出
   - `_generate_shots`：将每个 `shot_request` 转成 `ShotGenerationRequest`，经 `Wan26RetryAdapter` 提交/轮询，获得 `ShotGenerationResponse(task_id, status, video_url)`；`Wan26Downloader` 下载视频。
   - `FFmpegSplitter.split_video_audio` 拆分 `video_path`/`audio_path`，`AssetStorage` 生成 `video_url`/`audio_url` 并落盘至 `static/{video,audio}`。
   - 生成 `shot_assets[]`（写入 `JobModel.shot_assets`），单条结构示例：`{shot_id, seed, model_task_id, raw_video_url, video_url, audio_url, video_path, audio_path, duration_s, resolution}`。
   - `AssetStorage.write_job_metadata` 输出 `static/metadata/{job_id}.json`，包含 `job_id`、`ir`、`shot_plan`、`shot_requests`、`shot_assets`、`state_transitions`、`total_duration_s` 等；`GET /v1/t2v/jobs/{job_id}` 返回 URL 与状态。
