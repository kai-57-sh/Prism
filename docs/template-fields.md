# 模板关键字段说明（产品视角，当前实现）

## 1. 模板在产品中的作用
- **模板匹配入口**：通过模板标签与 IR 进行语义检索或关键词兜底匹配，决定选择哪个模板。
- **镜头结构骨架**：模板提供镜头数量、时长、镜头类型与基础文案结构，LLM 在此基础上生成具体镜头计划。
- **生成约束**：负向提示词基底用于限制不希望出现的画面内容。

## 2. 字段清单（按影响范围）

### 2.1 影响模板匹配
- `template_id`（string）：模板唯一标识，用于日志、任务记录、版本关联。
- `version`（string）：模板版本号，用于精准匹配。
- `tags`（object）：模板标签，参与语义检索与关键词兜底。
  - `topic`（list[string]）：主题关键词（语义检索 + 关键词兜底）。
  - `style`（list[string]）：风格标签（语义检索 + 关键词兜底）。
  - `emotion`（list[string]）：情绪标签（语义检索 + 关键词兜底）。
  - `tone`（list[string]）：语气标签（仅语义检索）。
  - `subtitle_policy`（string）：字幕策略（IR 侧不参与检索计算，因此当前不会提升匹配；可用于后续补齐镜头计划）。
- `constraints.watermark_default`（bool，可选）：若存在，会被加入语义检索文本，用于提升匹配信号。

### 2.2 影响镜头计划与内容生成
- `shot_skeletons`（list[object]）：镜头骨架列表，LLM 用其生成 `ShotPlan`。
  - `shot_id`（string）：镜头标识（如 `S1`），用于镜头序号与资产命名。
  - `role`（string）：镜头角色（`hook` / `mechanism` / `payoff`），用于提示镜头功能。
  - `duration_s`（int）：镜头时长（秒）。
  - `camera`（object）：镜头类型与运动。
    - `type`（string）：镜头类型（如 `close_up` / `medium`）。
    - `motion`（string）：镜头运动（如 `slow_push_in` / `handheld`）。
  - `visual_template`（string）：视觉描述模板，LLM 用其生成具体画面。
  - `audio_template`（object）：音频描述模板。
    - `ambient`（string）：环境音描述。
    - `narration`（string）：旁白文本。
  - `subtitle_policy`（string）：该镜头字幕策略。
- `constraints.subtitle_policy` / `tags.subtitle_policy`（string）：当 LLM 未明确输出字幕策略时，会用于补齐 `ShotPlan.subtitle_policy`。

### 2.3 影响负向提示词
- `negative_prompt_base`（string）：负向提示词基底，会与系统追加的负向词合并，影响生成内容。

### 2.4 作为描述性元数据（当前不参与校验）
- `constraints` 其余字段（如 `duration_s_min/max`、`resolution_options`、`prompt_extend_allowed`）会入库，但**当前不驱动校验或参数覆盖**。

## 3. 当前实现的限制（产品需要知晓）
- 顶层 `audio_strategy`、`emotion_curve` 在模板文件中存在，但**未入库**，运行时不可用。
- 模板加载流程直接写入 JSON 字段，**不经过模板校验器**；字段正确性依赖模板文件本身。
- 关键词兜底仅使用 `topic/style/emotion`，`tone` 不参与兜底匹配。
