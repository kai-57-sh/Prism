# Case: Hypertension Mechanism (Explainer/3D Style)
## User Query(Input)
"请用3D动画风格解释高血压的原理，最好用‘水管和水流’做比喻，让老年人也能看懂。"

## Script Output(JSON)
```json
{
  "template_id": "med_hypertension_explainer",
  "version": "1.0.0",
  "tags": {
    "topic": ["hypertension", "blood_pressure", "health_education"],
    "emotion": ["tense", "informative", "relaxed"],
    "style": ["explainer", "3d_render", "metaphor"],
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
  "emotion_curve": ["urgent", "analytical", "safe"],
  "shot_skeletons": [
    {
      "shot_id": "S1",
      "role": "hook",
      "duration_s": 4,
      "camera": {
        "type": "close_up",
        "motion": "static"
      },
      "visual_template": "3D animation style. A cute red heart character pumping rapidly, sweating, looking stressed. A red warning light pulsing in the background. High quality 3D render, blender style, soft edges, 720p.",
      "audio_template": {
        "ambient": "fast heartbeat sound, alarm beep",
        "narration": "头晕心慌？你的血管可能正在承受‘高压’危机！"
      },
      "subtitle_policy": "auto"
    },
    {
      "shot_id": "S2",
      "role": "mechanism",
      "duration_s": 7,
      "camera": {
        "type": "medium",
        "motion": "pan_right"
      },
      "visual_template": "Visual metaphor. A transparent garden hose (representing a blood vessel). The water inside is flowing too fast and the hose is expanding, looking like it might burst. The hose is being squeezed by a clamp. Bright, clean educational style.",
      "audio_template": {
        "ambient": "water rushing sound, squeaking rubber",
        "narration": "高血压就像水管里的水压过大。血管壁变硬变窄，心脏泵血越来越费力。"
      },
      "subtitle_policy": "auto"
    },
    {
      "shot_id": "S3",
      "role": "payoff",
      "duration_s": 4,
      "camera": {
        "type": "medium",
        "motion": "slow_zoom_out"
      },
      "visual_template": "The hose relaxes and water flows smoothly and gently. The background turns from red to a calm cool blue. The heart character looks happy and relaxed. Soft studio lighting.",
      "audio_template": {
        "ambient": "gentle stream flow, harp music",
        "narration": "控制血压，给血管减负，让生命之河平稳流淌。"
      },
      "subtitle_policy": "auto"
    }
  ],
  "negative_prompt_base": "text, anatomy chart, blood, gore, realistic surgery, scary, dark, low resolution"
}