# Case: Dry Eye (LifeStyle)
## User Query(Input)
"帮我生成一个关于手机眼干眼涩的科普短视频，要Vlog风格，适合发小红书，重点讲怎么缓解。"

## Script Output(JSON)
```json
{
  "template_id": "med_dry_eye",
  "version": "1.0.0",
  "tags": {
    "topic": ["dry_eye", "lifestyle", "bedroom", "phone"],
    "emotion": ["annoyed", "informative", "relaxed"],
    "style": ["lifestyle", "real_person", "vlog"],
    "subtitle_policy": "auto"
  },
  "constraints": {
    "duration_s_min": 2,
    "duration_s_max": 15,
    "resolution_options": ["720P", "1080P"],
    "subtitle_policy": "auto",
    "prompt_extend_allowed": true
  },
  "audio_strategy": "strategy_a",
  "emotion_curve": ["tired", "calm", "happy"],
  "shot_skeletons": [
    {
      "shot_id": "S1",
      "role": "hook",
      "duration_s": 4,
      "camera": {
        "type": "close_up",
        "motion": "slow_push_in"
      },
      "visual_template": "Cinematic vlog shot, dark bedroom. Close-up of a young person's face illuminated solely by the harsh blue light of a smartphone screen. Visible redness in eyes, expression of fatigue. High contrast lighting, realistic texture, 720p masterpiece.",
      "audio_template": {
        "ambient": "bedroom silence, slight fabric rustle",
        "narration": "盯屏后眼干痒酸胀？别只当眼疲劳！"
      },
      "subtitle_policy": "auto"
    },
    {
      "shot_id": "S2",
      "role": "mechanism",
      "duration_s": 6,
      "camera": {
        "type": "medium",
        "motion": "handheld"
      },
      "visual_template": "Warm indoor lighting, cozy atmosphere. The person sits on the bed, gently applying preservative-free artificial tears. In the background, a humidifier emits a visible stream of soft mist (volumetric fog). High aesthetic quality, soft focus background.",
      "audio_template": {
        "ambient": "soft humidifier hiss, water drop sound",
        "narration": "症状持续可能是干眼症。多眨眼、滴人工泪液，给眼睛补足水分。"
      },
      "subtitle_policy": "auto"
    },
    {
      "shot_id": "S3",
      "role": "payoff",
      "duration_s": 4,
      "camera": {
        "type": "close_up",
        "motion": "slow_zoom_out"
      },
      "visual_template": "Morning sunlight streaming through the window (God rays). The person smiles at the camera, eyes looking clear and hydrated. Fresh and airy color grading, detailed skin texture, photorealistic.",
      "audio_template": {
        "ambient": "morning birds chirping, uplifting music swell",
        "narration": "做好这些，缓解不适，守护双眼健康~"
      },
      "subtitle_policy": "auto"
    }
  ],
  "negative_prompt_base": "text, subtitles, watermark, logo, distorted face, ugly eyes, cartoon, low quality"
}