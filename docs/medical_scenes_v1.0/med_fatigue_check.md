# Case: Fatigue Status Check(LifeStyle)
## User Query(Input)
"做一个‘晨起疲劳自测’的视频，主要道具是握力器，教大家通过握力数值快速判断身体状态。"

## Script Output(JSON)
```json
{
  "template_id": "med_fatigue_check",
  "version": "1.0.0",
  "tags": {
    "topic": ["fatigue", "health_check", "morning_routine", "grip_strength"],
    "emotion": ["tired", "focused", "assured"],
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
  "emotion_curve": ["tired", "focused", "assured"],
  "shot_skeletons": [
    {
      "shot_id": "S1",
      "role": "hook",
      "duration_s": 4,
      "camera": {
        "type": "medium",
        "motion": "static"
      },
      "visual_template": "Cinematic morning shot. A young person sitting on the edge of the bed in pajamas, looking messy and exhausted. They rub their stiff neck and shoulders. Soft, slightly cool morning light (blue hour vibe). High realism, 720p masterpiece.",
      "audio_template": {
        "ambient": "morning ambiance, heavy sigh, fabric rustle",
        "narration": "总觉得疲惫乏力，不知是否疲劳堆积？"
      },
      "subtitle_policy": "auto"
    },
    {
      "shot_id": "S2",
      "role": "mechanism",
      "duration_s": 7,
      "camera": {
        "type": "close_up",
        "motion": "slow_zoom_in"
      },
      "visual_template": "High-detail action shot. Close-up of a hand firmly squeezing a grip strength tester (dynamometer). The muscles in the forearm tense up. Warm morning sunlight illuminates the hand, creating strong texture and depth. Photorealistic.",
      "audio_template": {
        "ambient": "spring compression sound, deep breath",
        "narration": "握力测试能快速自检。晨起测一测，数值持续偏低，就是身体在喊累。"
      },
      "subtitle_policy": "auto"
    },
    {
      "shot_id": "S3",
      "role": "payoff",
      "duration_s": 4,
      "camera": {
        "type": "medium",
        "motion": "handheld"
      },
      "visual_template": "The person puts the device down and looks at the camera with a relieved, knowing smile. The room is now filled with bright, cheerful sunlight. High aesthetic score, clean and fresh vibe.",
      "audio_template": {
        "ambient": "uplifting chime, birds singing",
        "narration": "简单一测，科学判断疲劳，精准管理身体状态~"
      },
      "subtitle_policy": "auto"
    }
  ],
  "negative_prompt_base": "text, subtitles, watermark, logo, distorted hand, extra fingers, missing fingers, gym equipment background, dark room"
}