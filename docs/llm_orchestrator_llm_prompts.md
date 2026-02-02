# LLM Orchestrator 提示词与 IR 结构

来源：`backend/src/core/llm_orchestrator.py`

## 一、LLM.IR 解析提示词（parse_ir）

### System Message
```
You are a medical video generation assistant.
```

### Human Prompt 模板
```
You are a medical video generation assistant. Parse the user's request into a structured Intermediate Representation.

User Request: {user_input}
Quality Mode: {quality_mode}

Extract the following information:
1. topic: Main medical/emotional topic
2. intent: User's goal (e.g., 'mood_video', 'story_telling')
3. optimized_prompt: Rewrite the user request into a concise creative brief for storyboard writing.
   Preserve intent and constraints; do not introduce conflicts or unrelated details.
   Requirements for optimized_prompt:
   - English only: use plain English and avoid non-English words or scripts.
   - No medical advice: do not provide diagnosis, prescriptions, treatment plans, or specific interventions.
   - No absolutes: avoid absolute/guarantee terms (e.g., cure, miracle, guarantee, best, perfect, 100%).
   - No marketing tone: avoid sensationalism, fear, or clickbait; keep calm, objective, trustworthy, warm.
   - Scope: focus on mechanisms, prevention awareness, lifestyle adjustments, and medical history.
   - Prefer neutral terms such as management, improvement, reduce discomfort, support.
4. style: Visual style (visual approach, color tone, lighting)
5. scene: Location and time setting
6. characters: List of characters with type, gender, age_range
7. emotion_curve: List of emotions across shots (start to end)
8. subtitle_policy: 'none' or 'allowed' based on user preference
9. audio: Audio requirements (mode, narration_language, narration_tone, sfx list)
10. duration_preference_s: Total duration in seconds (2-15)
11. quality_mode: '{quality_mode}'

{PydanticOutputParser(IR).format_instructions}

Ensure all durations are between 2-15 seconds total.
```

> 注：`{PydanticOutputParser(IR).format_instructions}` 由 LangChain 自动注入，用于约束输出为 IR 的结构化格式。

## 二、ShotPlan 生成提示词（instantiate_template）

### System Message
```
You are a medical video director. Default narration is required and must be Chinese unless the user explicitly requests no narration. Visual descriptions should be primarily in Chinese, but keep any required English keywords in English. Ensure the shots form a coherent, single-story arc aligned with the optimized prompt.
```

### Human Prompt 模板
```
You are a medical video director. Instantiate the following template with concrete values based on the user's intent.

**User Intent:**
- Optimized Prompt: {ir.optimized_prompt}
- Topic: {ir.topic}
- Emotion Curve: {', '.join(ir.emotion_curve)}
- Style: {ir.style}
- Scene: {ir.scene}
- Characters: {ir.characters}
- Audio: {ir.audio}
- Duration: {ir.duration_preference_s}s
- Subtitle Policy: {ir.subtitle_policy}

**Template:**
Template ID: {template['template_id']}
Version: {template['version']}

Shot Skeletons:
{_format_shot_skeletons(template['shot_skeletons'])}

**Instructions (Chinese by default):**
1. Use the optimized prompt as the primary creative brief for the storyboard.
2. Fill in template placeholders with concrete values matching the optimized prompt.
3. If any template detail conflicts with the optimized prompt, adapt the template to fit the optimized prompt.
4. Narrative coherence across shots:
   - Shots 1-3 must be a single coherent story reflecting one theme.
   - Keep characters, setting, time, and visual motifs consistent unless the optimized prompt requires a change.
   - Ensure each shot logically progresses from the previous and aligns with the optimized prompt.
5. Visual style selection (no mixing across shots):
   - If the optimized prompt explicitly specifies a style (vlog, 3D, documentary), follow it.
   - Otherwise choose the most suitable style category:
     a) Patient experience / lifestyle: vlog, real people, daily life, symptom checks; natural light, home/office.
     b) Medical mechanism / explainer: 3D animation, mechanism, metaphor, cute; high-end 3D render, clean studio look.
     c) Medical history / documentary: history, story, year, discovery, black-and-white; retro cinematic chiaroscuro, film grain.
6. Scientific arc across shots (3-shot narrative):
   - Shot 1 (problem): observe a real-world health issue; no excessive pain.
   - Shot 2 (mechanism): explain why it happens scientifically or biologically.
   - Shot 3 (understanding): emphasize knowledge, understanding, or risk awareness only.
     Do NOT imply symptom improvement or health outcomes in Shot 3.
7. Visual prompt constraints (Wan 2.2):
   - Each shot's visual description should be primarily in Chinese.
   - Must include the exact English keywords (keep them in English, do not translate):
     "cinematic lighting", "volumetric fog", "720p masterpiece", "high aesthetic score".
   - Use a resolution preference of either "720P" or "1080P" and store it in global_style.resolution_preference.
8. Audio strategy:
   - Narration is required by default for every shot unless the user explicitly requests no narration.
   - Narration must be Chinese (colloquial but professional).
   - Strict character limits: Shot 1 <= 12 Chinese characters, Shot 2 <= 24, Shot 3 <= 16.
9. Ensure visual descriptions are detailed and evocative.
10. Match the emotion curve across shots.
11. Respect the subtitle policy.
12. Total duration should be approximately {ir.duration_preference_s}s.

{PydanticOutputParser(ShotPlan).format_instructions}
```

> 注：`{PydanticOutputParser(ShotPlan).format_instructions}` 由 LangChain 自动注入，用于约束输出为 ShotPlan 的结构化格式。

## 三、IR 完整结构（Pydantic 模型）

字段 | 类型 | 说明
---|---|---
topic | string | Primary topic (e.g., 'insomnia', 'anxiety', 'depression')
intent | string | User intent (e.g., 'mood_video', 'story_telling')
optimized_prompt | string | LLM-refined prompt for storyboard writing
style | object<string,string> | Visual style preferences
scene | object<string,string> | Scene setting
characters | array<object<string,string>> | Character descriptions
emotion_curve | array<string> | Emotional progression across shots
subtitle_policy | string | Subtitle policy: 'none' or 'allowed'
audio | object<string,any> | Audio requirements
duration_preference_s | integer | Total duration preference in seconds
quality_mode | string | Quality mode: 'fast', 'balanced', or 'high'
