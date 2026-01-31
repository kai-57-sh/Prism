#!/usr/bin/env python
"""
Qwen LLM 集成测试脚本
测试 ModelScope Qwen3-235B-A22B-Instruct-2507 语言模型
"""

import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_basic_qwen_call():
    """测试基本的 Qwen 模型调用"""
    print("\n" + "="*60)
    print("测试 1: 基本 Qwen 模型调用")
    print("="*60)

    from langchain_openai import ChatOpenAI
    from langchain.schema import HumanMessage
    from src.config.settings import settings

    llm = ChatOpenAI(
        model=settings.qwen_model,
        api_key=settings.modelscope_api_key,
        base_url=settings.modelscope_base_url,
        temperature=0.0,
    )

    messages = [HumanMessage(content="你好，请用一句话介绍你自己。")]

    print(f"📝 发送消息: {messages[0].content}")
    response = llm.invoke(messages)

    print(f"✅ 响应成功")
    print(f"📄 响应内容: {response.content}")
    print(f"📊 响应长度: {len(response.content)} 字符")

    assert response.content, "响应内容为空"
    assert len(response.content) > 0, "响应长度为0"

    return True


def test_qwen_with_system_message():
    """测试带系统消息的 Qwen 调用"""
    print("\n" + "="*60)
    print("测试 2: 带系统消息的 Qwen 调用")
    print("="*60)

    from langchain_openai import ChatOpenAI
    from langchain.schema import HumanMessage, SystemMessage
    from src.config.settings import settings

    llm = ChatOpenAI(
        model=settings.qwen_model,
        api_key=settings.modelscope_api_key,
        base_url=settings.modelscope_base_url,
        temperature=0.0,
    )

    messages = [
        SystemMessage(content="你是一个医疗视频生成助手。"),
        HumanMessage(content="请生成一个关于失眠的简短描述。")
    ]

    print(f"📝 系统消息: {messages[0].content}")
    print(f"📝 用户消息: {messages[1].content}")

    response = llm.invoke(messages)

    print(f"✅ 响应成功")
    print(f"📄 响应内容: {response.content}")

    assert response.content, "响应内容为空"
    assert "失眠" in response.content or "睡眠" in response.content, "响应内容与主题不符"

    return True


def test_qwen_json_output():
    """测试 Qwen JSON 输出"""
    print("\n" + "="*60)
    print("测试 3: Qwen JSON 输出")
    print("="*60)

    from langchain_openai import ChatOpenAI
    from langchain.schema import HumanMessage
    from src.config.settings import settings

    llm = ChatOpenAI(
        model=settings.qwen_model,
        api_key=settings.modelscope_api_key,
        base_url=settings.modelscope_base_url,
        temperature=0.0,
    )

    prompt = """请以 JSON 格式返回以下信息：
{
    "topic": "失眠",
    "intent": "mood_video",
    "emotion": ["焦虑", "平静"]
}

只返回 JSON，不要其他内容。"""

    messages = [HumanMessage(content=prompt)]

    print(f"📝 发送提示: {prompt[:50]}...")

    response = llm.invoke(messages)

    print(f"✅ 响应成功")
    print(f"📄 响应内容: {response.content}")

    # Try to parse JSON
    try:
        parsed = json.loads(response.content)
        print(f"📊 解析后的 JSON: {json.dumps(parsed, ensure_ascii=False, indent=2)}")
        assert "topic" in parsed, "JSON 中缺少 'topic' 字段"
        assert "intent" in parsed, "JSON 中缺少 'intent' 字段"
        print(f"✅ JSON 解析成功")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        raise

    return True


def test_qwen_chinese_understanding():
    """测试 Qwen 中文理解能力"""
    print("\n" + "="*60)
    print("测试 4: Qwen 中文理解能力")
    print("="*60)

    from langchain_openai import ChatOpenAI
    from langchain.schema import HumanMessage
    from src.config.settings import settings

    llm = ChatOpenAI(
        model=settings.qwen_model,
        api_key=settings.modelscope_api_key,
        base_url=settings.modelscope_base_url,
        temperature=0.0,
    )

    messages = [
        HumanMessage(content="请将'焦虑'、'失眠'、'放松'这三个词按情绪从负面到正面排序。")
    ]

    print(f"📝 发送消息: {messages[0].content}")

    response = llm.invoke(messages)

    print(f"✅ 响应成功")
    print(f"📄 响应内容: {response.content}")

    assert response.content, "响应内容为空"

    return True


def test_qwen_structured_extraction():
    """测试 Qwen 结构化信息提取"""
    print("\n" + "="*60)
    print("测试 5: Qwen 结构化信息提取")
    print("="*60)

    from langchain_openai import ChatOpenAI
    from langchain.schema import HumanMessage
    from src.config.settings import settings

    llm = ChatOpenAI(
        model=settings.qwen_model,
        api_key=settings.modelscope_api_key,
        base_url=settings.modelscope_base_url,
        temperature=0.0,
    )

    user_input = "我想要一个关于失眠的舒缓视频，时长 10 秒，暖色调"

    prompt = f"""从以下用户输入中提取结构化信息：

用户输入: {user_input}

请以 JSON 格式返回：
{{
    "topic": "主题",
    "intent": "意图",
    "duration_preference_s": 时长（数字），
    "color_tone": "色调"
}}

只返回 JSON。"""

    messages = [HumanMessage(content=prompt)]

    print(f"📝 用户输入: {user_input}")
    print(f"📝 发送提示: {prompt[:80]}...")

    response = llm.invoke(messages)

    print(f"✅ 响应成功")
    print(f"📄 响应内容: {response.content}")

    try:
        parsed = json.loads(response.content)
        print(f"📊 解析后的 JSON: {json.dumps(parsed, ensure_ascii=False, indent=2)}")

        # Validate extracted information
        assert "topic" in parsed, "JSON 中缺少 'topic' 字段"
        assert parsed["topic"] == "失眠" or "失眠" in parsed["topic"], f"主题提取错误: {parsed['topic']}"

        if "duration_preference_s" in parsed:
            print(f"✅ 主题: {parsed['topic']}")
            print(f"✅ 时长: {parsed.get('duration_preference_s', 'N/A')} 秒")
            print(f"✅ 色调: {parsed.get('color_tone', 'N/A')}")

        print(f"✅ 信息提取成功")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        print(f"   原始响应: {response.content}")
        raise

    return True


def test_llm_orchestrator_parse_ir():
    """测试 LLM Orchestrator 的 IR 解析功能"""
    print("\n" + "="*60)
    print("测试 6: LLM Orchestrator - IR 解析")
    print("="*60)

    from src.core.llm_orchestrator import LLMOrchestrator

    orchestrator = LLMOrchestrator()

    # Test simple input
    user_input = "我想要一个关于失眠的舒缓视频"

    print(f"📝 用户输入: {user_input}")

    ir = orchestrator.parse_ir(user_input, quality_mode="balanced")

    print(f"✅ IR 解析成功")
    print(f"📊 IR 内容:")
    print(f"   - 主题: {ir.topic}")
    print(f"   - 意图: {ir.intent}")
    print(f"   - 时长: {ir.duration_preference_s} 秒")
    print(f"   - 质量模式: {ir.quality_mode}")
    print(f"   - 风格: {ir.style}")
    print(f"   - 场景: {ir.scene}")
    print(f"   - 情绪曲线: {ir.emotion_curve}")

    assert ir.topic, "IR 中缺少主题"
    assert ir.intent, "IR 中缺少意图"
    assert ir.duration_preference_s > 0, "IR 中时长应该大于0"
    assert ir.quality_mode == "balanced", "IR 中质量模式不正确"

    return True


def test_llm_orchestrator_detailed_ir():
    """测试 LLM Orchestrator 的详细 IR 解析"""
    print("\n" + "="*60)
    print("测试 7: LLM Orchestrator - 详细 IR 解析")
    print("="*60)

    from src.core.llm_orchestrator import LLMOrchestrator

    orchestrator = LLMOrchestrator()

    user_input = """我想要一个10秒的视频，主题是失眠治疗。
风格要舒缓、暖色调。场景设定在卧室。
情绪从焦虑逐渐转为平静。不需要字幕。"""

    print(f"📝 用户输入: {user_input}")

    ir = orchestrator.parse_ir(user_input, quality_mode="high")

    print(f"✅ IR 解析成功")
    print(f"📊 IR 内容:")
    print(f"   - 主题: {ir.topic}")
    print(f"   - 意图: {ir.intent}")
    print(f"   - 时长: {ir.duration_preference_s} 秒")
    print(f"   - 质量模式: {ir.quality_mode}")
    print(f"   - 风格: {ir.style}")
    print(f"   - 场景: {ir.scene}")
    print(f"   - 情绪曲线: {ir.emotion_curve}")
    print(f"   - 字幕策略: {ir.subtitle_policy}")

    # Accept both Chinese and English topic (LLM may translate)
    assert ir.topic in ["失眠", "insomnia", "失眠治疗"] or "失眠" in ir.topic or "insomnia" in ir.topic.lower(), \
        f"主题应该是'失眠'相关，实际是: {ir.topic}"
    assert ir.style, "IR 中缺少风格信息"
    assert ir.scene, "IR 中缺少场景信息"
    assert len(ir.emotion_curve) >= 2, "情绪曲线应该至少有2个元素"
    assert ir.duration_preference_s == 10, "时长应该是10秒"

    return True


def main():
    """主测试函数"""
    print("\n" + "╔" + "="*58 + "╗")
    print("║" + " "*10 + "Qwen LLM 集成测试套件" + " "*20 + "║")
    print("╚" + "="*58 + "╝")

    # 检查环境变量
    print("\n🔍 检查环境配置...")
    if not os.getenv("MODELSCOPE_API_KEY"):
        print("❌ MODELSCOPE_API_KEY 未设置")
        print("   请在 .env 文件中设置 MODELSCOPE_API_KEY")
        return False

    if not os.getenv("QWEN_MODEL"):
        print("❌ QWEN_MODEL 未设置")
        print("   请在 .env 文件中设置 QWEN_MODEL")
        return False

    print(f"✅ MODELSCOPE_API_KEY: {os.getenv('MODELSCOPE_API_KEY')[:20]}...")
    print(f"✅ QWEN_MODEL: {os.getenv('QWEN_MODEL')}")
    print(f"✅ MODELSCOPE_BASE_URL: {os.getenv('MODELSCOPE_BASE_URL')}")

    # 运行测试
    tests = [
        ("基本调用", test_basic_qwen_call),
        ("系统消息", test_qwen_with_system_message),
        ("JSON 输出", test_qwen_json_output),
        ("中文理解", test_qwen_chinese_understanding),
        ("信息提取", test_qwen_structured_extraction),
        ("IR 解析", test_llm_orchestrator_parse_ir),
        ("详细 IR 解析", test_llm_orchestrator_detailed_ir),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\n🧪 运行测试: {name}")
            test_func()
            passed += 1
            print(f"✅ 测试 '{name}' 通过")
        except Exception as e:
            failed += 1
            print(f"❌ 测试 '{name}' 失败: {str(e)}")
            import traceback
            traceback.print_exc()

    # 测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"✅ 通过: {passed}/{len(tests)}")
    print(f"❌ 失败: {failed}/{len(tests)}")
    print(f"📊 成功率: {passed/len(tests)*100:.1f}%")

    if failed == 0:
        print("\n🎉 所有测试通过！Qwen LLM 集成正常工作。")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查配置和网络连接。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
