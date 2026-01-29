"""
Quick Test Setup Verification
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv

# Load environment
load_dotenv()


def test_imports():
    """Test that all core modules can be imported"""
    print("=" * 60)
    print("Testing Module Imports")
    print("=" * 60)

    try:
        from src.core.input_processor import InputProcessor
        print("✓ InputProcessor imported")
    except Exception as e:
        print(f"✗ InputProcessor failed: {e}")
        return False

    try:
        from src.core.template_router import TemplateRouter
        print("✓ TemplateRouter imported")
    except Exception as e:
        print(f"✗ TemplateRouter failed: {e}")
        return False

    try:
        from src.core.llm_orchestrator import LLMOrchestrator
        print("✓ LLMOrchestrator imported")
    except Exception as e:
        print(f"✗ LLMOrchestrator failed: {e}")
        return False

    try:
        from src.core.validator import Validator
        print("✓ Validator imported")
    except Exception as e:
        print(f"✗ Validator failed: {e}")
        return False

    try:
        from src.core.prompt_compiler import PromptCompiler
        print("✓ PromptCompiler imported")
    except Exception as e:
        print(f"✗ PromptCompiler failed: {e}")
        return False

    try:
        from src.core.wan26_adapter import Wan26Adapter, Wan26RetryAdapter
        print("✓ Wan26Adapter imported")
    except Exception as e:
        print(f"✗ Wan26Adapter failed: {e}")
        return False

    try:
        from src.services.job_manager import JobManager
        print("✓ JobManager imported")
    except Exception as e:
        print(f"✗ JobManager failed: {e}")
        return False

    try:
        from src.services.storage import JobDB, TemplateDB
        print("✓ Storage services imported")
    except Exception as e:
        print(f"✗ Storage services failed: {e}")
        return False

    print()
    return True


def test_environment():
    """Test environment configuration"""
    print("=" * 60)
    print("Testing Environment Configuration")
    print("=" * 60)

    from src.config.settings import settings

    # Check API keys
    has_dashscope = bool(settings.dashscope_api_key)
    has_modelscope = bool(settings.modelscope_api_key)

    print(f"DASHSCOPE_API_KEY: {'✓ Configured' if has_dashscope else '✗ Missing'}")
    print(f"MODELSCOPE_API_KEY: {'✓ Configured' if has_modelscope else '✗ Missing'}")
    print(f"MODELSCOPE_BASE_URL: {settings.modelscope_base_url}")
    print(f"QWEN_MODEL: {settings.qwen_model}")
    print(f"DATABASE_URL: {settings.database_url}")
    print(f"REDIS_URL: {settings.redis_url}")

    print()

    # Warn if API keys are missing
    if not has_dashscope:
        print("⚠ Warning: DASHSCOPE_API_KEY not set")
        print("  Integration tests for Wan2.6 will be skipped")
        print()

    if not has_modelscope:
        print("⚠ Warning: MODELSCOPE_API_KEY not set")
        print("  Integration tests for Qwen will be skipped")
        print()

    return True


def test_database():
    """Test database connection"""
    print("=" * 60)
    print("Testing Database Connection")
    print("=" * 60)

    try:
        from sqlalchemy import create_engine
        from src.models.job import Base

        # Use test database
        test_db_url = "sqlite:///./test_setup.db"
        engine = create_engine(test_db_url)

        # Create tables
        Base.metadata.create_all(engine)
        print("✓ Database tables created successfully")

        # Test connection
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        session.execute("SELECT 1")
        session.close()
        print("✓ Database connection successful")

        # Cleanup
        import os
        if os.path.exists("test_setup.db"):
            os.remove("test_setup.db")
            print("✓ Test database cleaned up")

        print()
        return True

    except Exception as e:
        print(f"✗ Database test failed: {e}")
        print()
        return False


def test_fixtures():
    """Test that fixtures are available"""
    print("=" * 60)
    print("Testing Test Fixtures")
    print("=" * 60)

    try:
        from tests.fixtures.sample_data import (
            SAMPLE_IR,
            SAMPLE_TEMPLATE,
            SAMPLE_SHOT_PLAN,
        )
        print("✓ Sample fixtures loaded")
        print(f"  - IR topic: {SAMPLE_IR['topic']}")
        print(f"  - Template ID: {SAMPLE_TEMPLATE['template_id']}")
        print(f"  - Shot plan shots: {len(SAMPLE_SHOT_PLAN['shots'])}")
        print()
        return True
    except Exception as e:
        print(f"✗ Fixtures failed: {e}")
        print()
        return False


def main():
    """Run all setup tests"""
    print("\n" + "=" * 60)
    print("Prism Backend Setup Verification")
    print("=" * 60)
    print()

    results = {
        "Imports": test_imports(),
        "Environment": test_environment(),
        "Database": test_database(),
        "Fixtures": test_fixtures(),
    }

    print("=" * 60)
    print("Setup Verification Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test_name}: {status}")

    total = len(results)
    passed = sum(results.values())

    print()
    print(f"Total: {passed}/{total} checks passed")

    if passed == total:
        print("\n✓ Setup verification successful! Ready to run tests.")
        print("\nRun tests:")
        print("  ./run_tests.sh unit          # Unit tests only")
        print("  ./run_tests.sh integration   # Integration tests")
        print("  ./run_tests.sh all           # All tests")
        return 0
    else:
        print(f"\n✗ {total - passed} check(s) failed. Please fix issues before running tests.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
