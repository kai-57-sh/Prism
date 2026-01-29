# Medical Scene Templates Summary

This directory contains JSON video generation templates for medical health education content.

## Template Files

### Newly Created (v1.0 - 2026-01-28)

1. **brain_fog_v1.json** - Brain fog improvement tips for office workers
   - Style: Lifestyle/Vlog
   - Emotions: confused → calm → confident
   - Shots: 3 (hook, mechanism, payoff)

2. **comedones_v1.json** - Skincare tips for closed comedones
   - Style: Lifestyle/Vlog
   - Emotions: annoyed → focused → happy
   - Shots: 3 (hook, mechanism, payoff)

3. **dry_eye_v1.json** - Digital eye strain relief
   - Style: Lifestyle/Vlog
   - Emotions: tired → calm → happy
   - Shots: 3 (hook, mechanism, payoff)

4. **fatigue_check_v1.json** - Morning fatigue self-test with grip strength
   - Style: Lifestyle/Vlog
   - Emotions: tired → focused → assured
   - Shots: 3 (hook, mechanism, payoff)

5. **gastritis_explainer_v1.json** - Stomach pain mechanism explanation
   - Style: 3D Explainer/Metaphor
   - Emotions: painful → cooling → happy
   - Shots: 3 (hook, mechanism, payoff)
   - Version: 1.1.0

6. **hypertension_explainer_v1.json** - Blood pressure mechanism with hose metaphor
   - Style: 3D Explainer/Metaphor
   - Emotions: urgent → analytical → safe
   - Shots: 3 (hook, mechanism, payoff)

7. **penicillin_history_v1.json** - Discovery of penicillin documentary
   - Style: Documentary/Retro/Cinematic
   - Emotions: mysterious → revelation → epic
   - Shots: 3 (hook, mechanism, payoff)
   - Setting: 1928 London laboratory

8. **sleep_strength_v1.json** - Strength training for better sleep
   - Style: Lifestyle/Vlog
   - Emotions: anxious → focused → peaceful
   - Shots: 3 (hook, mechanism, payoff)

9. **xray_history_v1.json** - Discovery of X-rays documentary
   - Style: Documentary/Noir/Vintage
   - Emotions: mysterious → scary → revolutionary
   - Shots: 3 (hook, mechanism, payoff)
   - Setting: 1895 Germany laboratory

### Existing Templates

- **anxiety_v1.json** - Anxiety management
- **depression_v1.json** - Depression education
- **insomnia_v1.json** - Insomnia relief

## Template Structure

All templates follow a consistent JSON schema:

```json
{
  "template_id": "unique_identifier",
  "version": "semantic_version",
  "tags": {
    "topic": ["keywords"],
    "emotion": ["emotion_curve"],
    "style": ["visual_style"],
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
  "emotion_curve": ["emotion_progression"],
  "shot_skeletons": [
    {
      "shot_id": "S1",
      "role": "hook|mechanism|payoff",
      "duration_s": number,
      "camera": {
        "type": "shot_type",
        "motion": "camera_movement"
      },
      "visual_template": "detailed_visual_prompt",
      "audio_template": {
        "ambient": "ambient_sound",
        "narration": "voiceover_text"
      },
      "subtitle_policy": "auto"
    }
  ],
  "negative_prompt_base": "quality_constraints"
}
```

## Style Categories

### Lifestyle/Vlog Style
- Real person footage
- Natural lighting
- Bedroom/office/bathroom settings
- Handheld or static camera
- Focus on relatable daily scenarios

### 3D Explainer/Metaphor Style
- 3D rendered characters (cute organs, props)
- Visual metaphors for medical concepts
- Bright, clean backgrounds
- Educational focus
- Blender-style renders

### Documentary/Historical Style
- Vintage/retro aesthetics
- Sepia or black and white grading
- Film grain effects
- Period-accurate settings
- Cinematic compositions

## Shot Roles

- **Hook**: Grab attention, present problem
- **Mechanism**: Explain the science/solution
- **Payoff**: Show positive outcome, call to action

## Usage

Templates are loaded by the Prism backend's `TemplateRouter` using FAISS semantic search. When a user query matches a template semantically, the template is instantiated with the LLM orchestrator to generate detailed shot prompts for video generation.

## Topics Covered

- Workplace health (brain fog, fatigue)
- Skincare (comedones)
- Eye health (dry eye)
- Digestive health (gastritis)
- Cardiovascular health (hypertension)
- Sleep health (insomnia, strength training)
- Medical history (penicillin, X-rays)

## Total Templates: 12
- 9 new medical scene templates
- 3 existing mental health templates
