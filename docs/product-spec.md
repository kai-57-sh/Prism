# 产品说明（当前实现）

## 1. 产品功能说明
- 文本生成视频（T2V），以“按镜头生成 + 结果聚合”为核心，不做全片合成。
- 通过 LLM 解析用户意图（IR）并实例化模板生成镜头计划。
- 按镜头调用 Wan2.6-t2v 生成视频，下载后拆分音频与视频文件。
- 任务结果落库并输出 metadata JSON，支持任务状态查询。
- 支持后续“定稿”和“修订”流程（以既有任务为基础重生成镜头）。

## 2. 工作流程（当前实现）
1. **请求提交与限流**
   - 入口：`POST /v1/t2v/generate`。
   - `RateLimiter` 做频次与并发限制，不通过即返回错误。

2. **输入处理**
   - `InputProcessor.process_input`：PII 脱敏、语言检测、对齐翻译。
   - 供 LLM 使用的文本：`aligned_text` 或 `redacted_text`。

3. **IR 解析（LLM）**
   - 系统提示词：
     - `You are a medical video generation assistant.`
   - `LLMOrchestrator.parse_ir` 生成 IR。
   - IR 完整结构（Pydantic）：
     ```text
     IR:
       topic: str
       intent: str
       style: Dict[str, str]
       scene: Dict[str, str]
       characters: List[Dict[str, str]]
       emotion_curve: List[str]
       subtitle_policy: str
       audio: Dict[str, Any]
       duration_preference_s: int
       quality_mode: str
     ```

4. **模板匹配**
   - `TemplateRouter.match_template` 使用 Embeddings 语义检索；缺 Embeddings 时走关键词兜底。
   - 选出最匹配的 `template_id/version` 与置信度。

5. **模板实例化与镜头计划（LLM）**
   - 系统提示词：
     - `You are a medical video director.`
   - `LLMOrchestrator.instantiate_template` 基于 IR + 模板 `shot_skeletons` 生成 `ShotPlan`。
   - `JobManager._normalize_shot_plan` 补齐/规范 `shot_id`、`duration_s` 等字段。

6. **参数校验**
   - `Validator.validate_parameters` 校验总时长、镜头数量、分辨率、quality 模式限制等。
   - 校验失败直接报错并终止流程。

7. **镜头请求编译**
   - `PromptCompiler.compile_shot_prompt` 生成 `shot_requests[]`。
   - 结构：`{shot_id, compiled_prompt, compiled_negative_prompt, params{size,duration,seed,prompt_extend,watermark}}`。

8. **任务落库与状态流转**
   - `JobDB.create_job` 写入 `ir/shot_plan/shot_requests/quality_mode/resolution` 等中间态。
   - 状态：`CREATED -> SUBMITTED -> RUNNING`。

9. **分镜生成与下载**
   - 每个镜头按 `QUALITY_MODES.preview_seeds` 进行多次生成，但当前每次使用相同 `seed`。
   - `Wan26RetryAdapter` 提交/轮询，`Wan26Downloader` 下载视频文件。

10. **音视频拆分与落盘**
   - `FFmpegSplitter` 拆分视频与音频；失败时仅保留视频并将 `audio_url` 置空。
   - `AssetStorage` 写入 `static/{video,audio}` 并生成 URL（视频子目录默认 `vedios`，带日期层级）。

11. **资产更新与元数据输出**
   - `JobDB.update_job_assets` 写入 `shot_assets[]`。
   - `AssetStorage.write_job_metadata` 输出 `static/metadata/{job_id}.json`。
   - 状态更新为 `SUCCEEDED`，失败则写入 `error_details` 并标记 `FAILED`。

12. **结果查询**
   - `GET /v1/t2v/jobs/{job_id}` 返回状态与分镜资源 URL。

## 3. 关键补充说明
- 生成接口返回 `202`，但当前实现会在服务端同步完成整个生成流程后才响应。
- `duration_preference_s` 与 `resolution` 当前不会直接影响生成参数：
  - 实际生成尺寸取自 `ir.get("resolution")`，IR 中未定义该字段，默认 `1280x720`。
  - `duration_preference_s` 未直接传入 LLM 链路，仅能通过 `user_prompt` 间接影响。
- 当前不做全片合成，输出为“按镜头拆分”的视频/音频文件。
- 预览候选未写入 `preview_shot_assets`，而是直接写入 `shot_assets`。
- 音频依赖 FFmpeg 拆分，FFmpeg 失败时只保留视频文件。
- 模板匹配（Embeddings 语义检索）：
  - 索引构建：将模板 `tags.topic/tone/style/emotion`、`template.emotion_curve`、`template_id`（含空格变体）、`constraints.watermark_default` 拼成文本，使用 DashScope Embeddings + FAISS 建索引（`normalize_L2=True`）。
  - 查询构造：从 IR 拼接 `topic`（含空格/下划线变体）、`intent`、`style.visual/visual_approach/visual_style/color_tone/lighting`、`scene.location/time`、`emotion_curve`。
  - 排序规则：FAISS 结果转为 `cosine_sim = 1 - (score/2)`，并与标签 Jaccard 相似度按 `0.7 * cosine + 0.3 * jaccard` 合成置信度；低于阈值（默认 `0.5`）判定无匹配。
- 模板匹配（关键词兜底）：
  - 触发条件：Embeddings 初始化失败或索引构建失败时进入兜底。
  - 主题匹配：IR `topic` 与模板 `tags.topic` 规范化比较，完全匹配得分 `1.0`，否则用分词交集比例。
  - 情绪匹配：IR `emotion_curve` 与模板 `tags.emotion` 交集比例。
  - 风格匹配：IR `style`（`visual/visual_approach/visual_style/color_tone/lighting`）与模板 `tags.style` 交集比例。
  - 置信度合成：`0.6 * topic + 0.2 * emotion + 0.2 * style`，低于阈值直接丢弃。
