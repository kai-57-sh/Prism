"""
Sample test data and fixtures
"""

import json
from typing import Dict, List, Any


# Sample IR data
SAMPLE_IR = {
    "topic": "失眠",
    "intent": "mood_video",
    "style": {
        "visual": "舒缓风格",
        "color_tone": "暖色调",
        "lighting": "柔和光线"
    },
    "scene": {
        "location": "卧室",
        "time": "夜晚"
    },
    "characters": [],
    "emotion_curve": ["焦虑", "平静", "安详"],
    "subtitle_policy": "none",
    "audio": {
        "mode": "tts",
        "narration_language": "zh-CN",
        "narration_tone": "舒缓",
        "sfx": ["轻柔音乐", "环境音"]
    },
    "duration_preference_s": 10,
    "quality_mode": "balanced"
}

# Sample template data
SAMPLE_TEMPLATE = {
    "template_id": "insomnia_relaxation",
    "version": "1.0",
    "shot_skeletons": [
        {
            "shot_id": 1,
            "duration_s": 3,
            "camera": "固定镜头",
            "visual_template": "宁静的卧室场景",
            "audio_template": "轻柔背景音乐",
            "subtitle_policy": "none"
        },
        {
            "shot_id": 2,
            "duration_s": 4,
            "camera": "缓慢推进",
            "visual_template": "人物逐渐放松",
            "audio_template": "舒缓旁白",
            "subtitle_policy": "allowed"
        },
        {
            "shot_id": 3,
            "duration_s": 3,
            "camera": "缓慢拉远",
            "visual_template": "安详入睡",
            "audio_template": "音乐渐弱",
            "subtitle_policy": "none"
        }
    ],
    "constraints": {
        "max_duration_s": 15,
        "min_duration_s": 5,
        "watermark_default": False
    },
    "tags": {
        "topic": ["失眠", "焦虑"],
        "tone": ["舒缓", "治愈"],
        "style": ["写实", "温暖"]
    }
}

# Sample shot plan data
SAMPLE_SHOT_PLAN = {
    "template_id": "insomnia_relaxation",
    "template_version": "1.0",
    "duration_s": 10,
    "subtitle_policy": "none",
    "shots": [
        {
            "shot_id": 1,
            "duration_s": 3,
            "camera": "固定镜头",
            "compiled_prompt": "宁静的卧室，月光透过窗户洒在床上",
            "compiled_negative_prompt": "",
            "audio": {
                "mode": "tts",
                "narration": "深呼吸，放松身体",
                "sfx": ["轻柔音乐"]
            },
            "seed": 12345
        },
        {
            "shot_id": 2,
            "duration_s": 4,
            "camera": "缓慢推进",
            "compiled_prompt": "人物躺在床上，表情逐渐放松",
            "compiled_negative_prompt": "",
            "audio": {
                "mode": "tts",
                "narration": "让思绪慢慢平静",
                "sfx": ["环境音"]
            },
            "seed": 12346
        },
        {
            "shot_id": 3,
            "duration_s": 3,
            "camera": "缓慢拉远",
            "compiled_prompt": "安详入睡的画面",
            "compiled_negative_prompt": "",
            "audio": {
                "mode": "tts",
                "narration": "晚安",
                "sfx": []
            },
            "seed": 12347
        }
    ],
    "global_style": {
        "visual": "舒缓风格",
        "color_tone": "暖色调",
        "lighting": "柔和光线"
    }
}

# Sample job data
SAMPLE_JOB = {
    "job_id": "test_job_123",
    "user_input_redacted": "我想要一个关于失眠的视频",
    "input_hash": "abc123def456",
    "ir": {
        "topic": "失眠",
        "intent": "mood_video",
        "style": {"visual": "舒缓"}
    },
    "shot_plan": {
        "template_id": "insomnia_relaxation",
        "shots": []
    },
    "shot_requests": [],
    "shot_assets": [],
    "state": "CREATED",
    "quality_mode": "balanced",
    "resolution": "1280*720"
}

# Sample shot assets
SAMPLE_SHOT_ASSETS = [
    {
        "shot_id": 1,
        "video_url": "https://example.com/video1.mp4",
        "audio_url": "https://example.com/audio1.mp3",
        "duration_s": 3,
        "resolution": "1280*720",
        "seed": 12345
    },
    {
        "shot_id": 2,
        "video_url": "https://example.com/video2.mp4",
        "audio_url": "https://example.com/audio2.mp3",
        "duration_s": 4,
        "resolution": "1280*720",
        "seed": 12346
    }
]

# Sample user inputs for testing
SAMPLE_USER_INPUTS = {
    "simple": "我想要一个关于失眠的视频",
    "detailed": """我想要一个10秒的视频，主题是失眠治疗。
风格要舒缓、暖色调。场景设定在卧室。
情绪从焦虑逐渐转为平静。不需要字幕。""",
    "with_pii": "我的邮箱是 test@example.com，想要一个焦虑主题的视频",
    "english": "I want a video about insomnia",
    "mixed": "Hello, 我想要关于insomnia的视频"
}

# Expected validation results
VALIDATION_RESULTS = {
    "valid_shot_plan": {
        "is_valid": True,
        "errors": []
    },
    "invalid_duration": {
        "is_valid": False,
        "errors": ["Shot duration exceeds maximum"]
    },
    "missing_prompt": {
        "is_valid": False,
        "errors": ["Missing compiled prompt"]
    }
}


def get_sample_ir(**overrides) -> Dict[str, Any]:
    """Get sample IR with optional overrides"""
    ir = SAMPLE_IR.copy()
    ir.update(overrides)
    return ir


def get_sample_template(**overrides) -> Dict[str, Any]:
    """Get sample template with optional overrides"""
    template = SAMPLE_TEMPLATE.copy()
    template.update(overrides)
    return template


def get_sample_shot_plan(**overrides) -> Dict[str, Any]:
    """Get sample shot plan with optional overrides"""
    plan = SAMPLE_SHOT_PLAN.copy()
    plan.update(overrides)
    return plan


def get_sample_job(**overrides) -> Dict[str, Any]:
    """Get sample job with optional overrides"""
    job = SAMPLE_JOB.copy()
    job.update(overrides)
    return job


def save_fixture_data():
    """Save fixture data to JSON files for manual inspection"""
    import os
    fixture_dir = os.path.join(os.path.dirname(__file__))

    with open(os.path.join(fixture_dir, 'sample_ir.json'), 'w') as f:
        json.dump(SAMPLE_IR, f, indent=2, ensure_ascii=False)

    with open(os.path.join(fixture_dir, 'sample_template.json'), 'w') as f:
        json.dump(SAMPLE_TEMPLATE, f, indent=2, ensure_ascii=False)

    with open(os.path.join(fixture_dir, 'sample_shot_plan.json'), 'w') as f:
        json.dump(SAMPLE_SHOT_PLAN, f, indent=2, ensure_ascii=False)

    print("Fixture data saved")


if __name__ == "__main__":
    save_fixture_data()
