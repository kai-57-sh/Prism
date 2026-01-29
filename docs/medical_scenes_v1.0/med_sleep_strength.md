# Case: Strength Training for Sleep(LifeStyle)
## User Query(Input)
"我需要一个视频告诉大家‘睡前做力量训练其实比有氧更助眠’，场景设定在家里卧室，动作要轻柔。"

## Script Output(JSON)
```json
{
  "template_id": "med_sleep_strength",
  "version": "1.0.0",
  "tags": {
    "topic": ["sleep", "insomnia", "fitness", "bedroom"],
    "emotion": ["anxious", "focused", "peaceful"],
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
  "emotion_curve": ["anxious", "focused", "peaceful"],
  "shot_skeletons": [
    {
      "shot_id": "S1",
      "role": "hook",
      "duration_s": 4,
      "camera": {
        "type": "close_up",
        "motion": "pan_left"
      },
      "visual_template": "Cinematic night shot. A young person lying in bed, tossing and turning, staring at the ceiling with wide, tired eyes. Blue moonlight contrasts with a dark room. Expression of frustration and insomnia. High grain, moody atmosphere, 720p masterpiece.",
      "audio_template": {
        "ambient": "clock ticking sound, heavy sigh",
        "narration": "长期睡眠浅、失眠，越熬越累？"
      },
      "subtitle_policy": "auto"
    },
    {
      "shot_id": "S2",
      "role": "mechanism",
      "duration_s": 7,
      "camera": {
        "type": "medium",
        "motion": "static"
      },
      "visual_template": "Warm, cozy bedroom setting with a bedside lamp on. The person is sitting on the edge of the bed, wearing comfortable pajamas, gently lifting a small dumbbell (bicep curl). Relaxed movement, not intense. Soft shadows, volumetric lighting, photorealistic.",
      "audio_template": {
        "ambient": "soft fabric rustle, gentle breath",
        "narration": "《PLOS ONE》证实：力量训练比有氧更助眠！睡前简单举举哑铃，每周两三次。"
      },
      "subtitle_policy": "auto"
    },
    {
      "shot_id": "S3",
      "role": "payoff",
      "duration_s": 4,
      "camera": {
        "type": "close_up",
        "motion": "slow_zoom_in"
      },
      "visual_template": "The person puts the dumbbell down and lies back on the pillow, closing their eyes with a peaceful, satisfied smile. The lighting dims slightly. High aesthetic score, comfort, deep sleep vibe.",
      "audio_template": {
        "ambient": "silence, heartbeat slowing down",
        "narration": "用力量训练，帮你找回婴儿般的睡眠~"
      },
      "subtitle_policy": "auto"
    }
  ],
  "negative_prompt_base": "text, subtitles, watermark, logo, gym equipment, heavy sweat, distorted face, extra limbs, bright daylight"
}