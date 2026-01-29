"""
Unit Tests for Validator
"""

import pytest
from src.core.validator import Validator, ValidationResult


class TestValidator:
    """Test suite for Validator"""

    @pytest.fixture
    def validator(self):
        """Create Validator instance"""
        return Validator()

    def test_validate_shot_plan_valid(self, validator: Validator, sample_shot_plan):
        """Test validation of valid shot plan"""
        result = validator.validate_shot_plan(
            sample_shot_plan,
            quality_mode="balanced"
        )

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_shot_plan_duration_too_long(self, validator: Validator, sample_shot_plan):
        """Test validation rejects shots that are too long"""
        # Make first shot too long
        sample_shot_plan["shots"][0]["duration_s"] = 20

        result = validator.validate_shot_plan(
            sample_shot_plan,
            quality_mode="balanced"
        )

        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("duration" in error.lower() for error in result.errors)

    def test_validate_shot_plan_total_duration(self, validator: Validator, sample_shot_plan):
        """Test validation of total duration"""
        # Make total duration too long
        sample_shot_plan["shots"][0]["duration_s"] = 8
        sample_shot_plan["shots"][1]["duration_s"] = 8
        sample_shot_plan["shots"][2]["duration_s"] = 8

        result = validator.validate_shot_plan(
            sample_shot_plan,
            quality_mode="balanced"
        )

        assert not result.is_valid
        assert any("total duration" in error.lower() for error in result.errors)

    def test_validate_shot_plan_missing_prompt(self, validator: Validator, sample_shot_plan):
        """Test validation rejects missing compiled prompt"""
        del sample_shot_plan["shots"][0]["compiled_prompt"]

        result = validator.validate_shot_plan(
            sample_shot_plan,
            quality_mode="balanced"
        )

        assert not result.is_valid
        assert any("prompt" in error.lower() for error in result.errors)

    def test_validate_quality_mode_fast(self, validator: Validator, sample_shot_plan):
        """Test validation for fast quality mode"""
        result = validator.validate_shot_plan(
            sample_shot_plan,
            quality_mode="fast"
        )

        # Fast mode should be more lenient
        assert result.is_valid or len(result.errors) < 3

    def test_validate_quality_mode_high(self, validator: Validator, sample_shot_plan):
        """Test validation for high quality mode"""
        result = validator.validate_shot_plan(
            sample_shot_plan,
            quality_mode="high"
        )

        # High mode should be stricter
        # But our sample_shot_plan is valid, so it should pass
        assert result.is_valid

    def test_validate_medical_compliance_safe_content(self, validator: Validator):
        """Test medical compliance validation for safe content"""
        prompt = "一个舒缓的失眠治疗视频，展示放松技巧"

        result = validator.validate_medical_compliance(prompt)

        assert result.is_compliant
        assert len(result.warnings) == 0

    def test_validate_medical_compliance_medical_advice(self, validator: Validator):
        """Test medical compliance validation for medical advice"""
        prompt = "你应该服用安眠药来治疗失眠"

        result = validator.validate_medical_compliance(prompt)

        # Should generate warning about medical advice
        assert not result.is_compliant or len(result.warnings) > 0

    def test_validate_resolution_valid(self, validator: Validator):
        """Test resolution validation"""
        assert validator.validate_resolution("1280*720")
        assert validator.validate_resolution("1920*1080")

    def test_validate_resolution_invalid(self, validator: Validator):
        """Test invalid resolution"""
        assert not validator.validate_resolution("640*480")
        assert not validator.validate_resolution("invalid")

    def test_validate_seed_count(self, validator: Validator):
        """Test seed count validation for quality modes"""
        # Fast mode: 1 seed
        assert validator.validate_seed_count(1, "fast")
        assert not validator.validate_seed_count(3, "fast")

        # Balanced mode: 2 seeds
        assert validator.validate_seed_count(2, "balanced")
        assert not validator.validate_seed_count(5, "balanced")

        # High mode: 3 seeds
        assert validator.validate_seed_count(3, "high")
        assert not validator.validate_seed_count(1, "high")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
