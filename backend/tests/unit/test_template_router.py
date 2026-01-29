"""
Unit Tests for Template Router
"""

import pytest
from src.core.template_router import TemplateRouter, TemplateMatch


class TestTemplateRouter:
    """Test suite for TemplateRouter"""

    @pytest.fixture
    def router(self):
        """Create TemplateRouter instance"""
        return TemplateRouter()

    def test_create_search_text(self, router: TemplateRouter):
        """Test search text creation from template"""
        template = {
            "template_id": "test_template",
            "version": "1.0",
            "tags": {
                "topic": ["失眠", "焦虑"],
                "tone": ["舒缓", "治愈"],
                "style": ["写实"]
            },
            "constraints": {
                "watermark_default": False
            }
        }

        search_text = router._create_search_text(template)

        assert "失眠" in search_text
        assert "焦虑" in search_text
        assert "舒缓" in search_text
        assert "治愈" in search_text
        assert "写实" in search_text
        assert "watermark" not in search_text  # False should not add keyword

    def test_build_index_empty_templates(self, router: TemplateRouter):
        """Test building index with empty template list"""
        router.build_index([])
        assert router.faiss_index is None

    def test_build_index_single_template(self, router: TemplateRouter):
        """Test building index with single template"""
        template = {
            "template_id": "test_template",
            "version": "1.0",
            "tags": {
                "topic": ["失眠"],
                "tone": ["舒缓"],
                "style": ["写实"]
            },
            "constraints": {}
        }

        # This test requires mocking embeddings
        # For now, we test the metadata setup
        router.build_index([template])

        key = f"test_template:1.0"
        assert key in router.template_metadata
        assert router.template_metadata[key]["template_id"] == "test_template"

    def test_calculate_jaccard_similarity_exact_match(self, router: TemplateRouter):
        """Test Jaccard similarity with exact match"""
        ir = {
            "topic": "失眠",
            "emotion_curve": ["焦虑", "平静"]
        }

        template = {
            "tags": {
                "topic": ["失眠", "焦虑"],
                "tone": ["舒缓"]
            }
        }

        similarity = router._calculate_jaccard_similarity(ir, template)

        # Should have good overlap
        assert similarity > 0.0
        assert similarity <= 1.0

    def test_calculate_jaccard_similarity_no_match(self, router: TemplateRouter):
        """Test Jaccard similarity with no match"""
        ir = {
            "topic": "抑郁",
            "emotion_curve": ["悲伤"]
        }

        template = {
            "tags": {
                "topic": ["失眠", "焦虑"],
                "tone": ["舒缓"]
            }
        }

        similarity = router._calculate_jaccard_similarity(ir, template)

        # Should have low or no overlap
        assert similarity >= 0.0
        assert similarity < 0.5

    def test_calculate_jaccard_similarity_empty_tags(self, router: TemplateRouter):
        """Test Jaccard similarity with empty tags"""
        ir = {"topic": "", "emotion_curve": []}
        template = {"tags": {}}

        similarity = router._calculate_jaccard_similarity(ir, template)

        # Should return 0.0 for empty tags
        assert similarity == 0.0

    def test_create_query_from_ir(self, router: TemplateRouter):
        """Test query creation from IR"""
        ir = {
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
            "emotion_curve": ["焦虑", "平静", "安详"]
        }

        query = router._create_query_from_ir(ir)

        assert "失眠" in query
        assert "mood_video" in query
        assert "舒缓风格" in query
        assert "暖色调" in query
        assert "卧室" in query
        assert "焦虑" in query
        assert "平静" in query
        assert "安详" in query

    def test_get_template_by_id(self, router: TemplateRouter, sample_template, test_db_session):
        """Test retrieving template by ID"""
        from src.services.storage import TemplateDB

        # Save template to database
        from src.models.template import TemplateModel
        db_template = TemplateModel(**sample_template)
        test_db_session.add(db_template)
        test_db_session.commit()

        # Retrieve template
        retrieved = router.get_template_by_id(
            sample_template["template_id"],
            sample_template["version"],
            test_db_session
        )

        assert retrieved is not None
        assert retrieved["template_id"] == sample_template["template_id"]
        assert retrieved["version"] == sample_template["version"]

    def test_get_template_by_id_not_found(self, router: TemplateRouter, test_db_session):
        """Test retrieving non-existent template"""
        retrieved = router.get_template_by_id(
            "nonexistent",
            "1.0",
            test_db_session
        )

        assert retrieved is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
