# Case: Discovery of Penicillin (Documentary/History Style)
## User Query(Input)
"生成一个关于弗莱明发现青霉素的纪录片风格脚本，要有1928年伦敦实验室的复古质感。"

## Script Output(JSON)
```json
{
  "template_id": "med_penicillin_history",
  "version": "1.0.0",
  "tags": {
    "topic": ["history", "penicillin", "science", "fleming"],
    "emotion": ["solemn", "mysterious", "hopeful"],
    "style": ["documentary", "retro", "cinematic"],
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
  "emotion_curve": ["mysterious", "revelation", "epic"],
  "shot_skeletons": [
    {
      "shot_id": "S1",
      "role": "hook",
      "duration_s": 5,
      "camera": {
        "type": "wide",
        "motion": "slow_push_in"
      },
      "visual_template": "London, 1928. A messy laboratory desk in a dimly lit room, cluttered with glass petri dishes and old books. Dust motes dancing in a single shaft of sunlight. Sepia tone, heavy film grain, vintage movie aesthetic, 720p masterpiece.",
      "audio_template": {
        "ambient": "ticking clock, distant London street noise",
        "narration": "1928年的伦敦，一个被遗忘在窗台的培养皿，即将改变人类的命运。"
      },
      "subtitle_policy": "auto"
    },
    {
      "shot_id": "S2",
      "role": "mechanism",
      "duration_s": 6,
      "camera": {
        "type": "macro",
        "motion": "static"
      },
      "visual_template": "Extreme macro shot of a petri dish. A fuzzy white mold colony (Penicillium) is growing in the center. Around it, there is a clear 'halo' where bacteria have been killed. Dramatic lighting highlights the 'halo'. Scientific breakthrough vibe, photorealistic.",
      "audio_template": {
        "ambient": "magical hum, microscope adjustment sound",
        "narration": "弗莱明意外发现，这团青霉菌周围形成了一个神秘的‘抑菌圈’，死神第一次退却了。"
      },
      "subtitle_policy": "auto"
    },
    {
      "shot_id": "S3",
      "role": "payoff",
      "duration_s": 4,
      "camera": {
        "type": "medium",
        "motion": "slow_pan"
      },
      "visual_template": "Transition to a black and white photo coming to life: A soldier in a WWII hospital bed sitting up and smiling, holding a vial of medicine. The image slowly saturates to color, symbolizing hope. Emotional cinematic score.",
      "audio_template": {
        "ambient": "orchestral swell, cheering",
        "narration": "从战场到病房，青霉素的诞生，让人类从此拥有了对抗感染的护盾。"
      },
      "subtitle_policy": "auto"
    }
  ],
  "negative_prompt_base": "text, subtitles, modern computer, colorful cartoon, low quality, distortion, bad anatomy"
}