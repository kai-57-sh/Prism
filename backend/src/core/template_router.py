"""
Template Router - FAISS-based semantic template matching
"""

from typing import List, Dict, Any, Optional, Tuple, Set
import re
import numpy as np
from langchain_community.vectorstores import FAISS
from pydantic import BaseModel

from src.config.settings import settings
from src.services.storage import TemplateDB
from src.services.observability import log_template_hit, logger
from sqlalchemy.orm import Session


class TemplateMatch(BaseModel):
    """Template match result with confidence score"""

    template_id: str
    version: str
    confidence: float
    confidence_components: Dict[str, float]
    template: Dict[str, Any]


class TemplateRouter:
    """
    Route user requests to appropriate medical scene templates using semantic search
    """

    def __init__(self):
        """Initialize template router using DashScope embeddings"""
        self.embeddings = None
        try:
            from langchain_community.embeddings import DashScopeEmbeddings

            self.embeddings = DashScopeEmbeddings(
                model=settings.embedding_model,
                dashscope_api_key=settings.dashscope_api_key,
            )
        except Exception as exc:
            logger.warning("embedding_init_failed", error=str(exc))
            self.embeddings = None
        self.faiss_index: Optional[FAISS] = None
        self.template_metadata: Dict[str, Dict[str, Any]] = {}

    def build_index(self, templates: List[Dict[str, Any]]) -> None:
        """
        Build FAISS index from templates

        Args:
            templates: List of template dictionaries
        """
        if not templates:
            return

        # Prepare texts and metadata
        texts = []
        metadata = []

        for template in templates:
            # Create searchable text from template
            text = self._create_search_text(template)
            texts.append(text)

            # Store metadata
            key = f"{template['template_id']}:{template['version']}"
            self.template_metadata[key] = template
            metadata.append({"key": key})

        # Build FAISS index
        if texts and self.embeddings is not None:
            try:
                self.faiss_index = FAISS.from_texts(
                    texts=texts,
                    embedding=self.embeddings,
                    metadatas=metadata,
                    normalize_L2=True,
                )
            except Exception as exc:
                logger.warning("embedding_index_build_failed", error=str(exc))
                # Allow metadata-only builds in unit tests without embeddings
                self.faiss_index = None

    def _normalize_tag(self, value: str) -> str:
        """Normalize tags for comparisons."""
        return re.sub(r"[_\s]+", "", value.strip().lower())

    def _create_search_text(self, template: Dict[str, Any]) -> str:
        """Create searchable text from template"""
        tags = template.get("tags", {})
        topic_list = tags.get("topic", [])
        tone_list = tags.get("tone", [])
        style_list = tags.get("style", [])
        emotion_list = tags.get("emotion", [])

        text_parts = []
        text_parts.extend(topic_list)
        text_parts.extend(tone_list)
        text_parts.extend(style_list)
        text_parts.extend(emotion_list)

        emotion_curve = template.get("emotion_curve", []) or []
        text_parts.extend(emotion_curve)

        template_id = template.get("template_id", "")
        if template_id:
            text_parts.append(template_id)
            text_parts.append(template_id.replace("_", " "))

        # Add constraint information
        constraints = template.get("constraints", {})
        if constraints.get("watermark_default"):
            text_parts.append("watermark")

        return " ".join(text_parts)

    def match_template(
        self,
        ir: Dict[str, Any],
        db: Session,
        top_k: int = 3,
        min_confidence: Optional[float] = None,
    ) -> Optional[TemplateMatch]:
        """
        Match IR to best template using semantic search and tag filtering

        Args:
            ir: Intermediate Representation
            db: Database session
            top_k: Number of candidates to consider
            min_confidence: Minimum confidence threshold

        Returns:
            TemplateMatch or None if no match found
        """
        if min_confidence is None:
            min_confidence = settings.template_match_min_confidence

        template_dicts: List[Dict[str, Any]] = []
        # Rebuild index if needed
        if self.faiss_index is None:
            templates = TemplateDB.list_templates(db)
            template_dicts = [t.to_dict() for t in templates]
            self.build_index(template_dicts)

        if self.faiss_index is None:
            # Fallback to keyword matching when embeddings are unavailable.
            return self._keyword_match(ir, template_dicts, top_k, min_confidence)

        # Create search query from IR
        query = self._create_query_from_ir(ir)

        # Search FAISS index
        try:
            results = self.faiss_index.similarity_search_with_score(query, k=top_k)

            if not results:
                return None

            # Rank results by combined confidence
            ranked = self._rank_results(ir, results)

            # Return best match if above threshold
            if ranked and ranked[0].confidence >= min_confidence:
                return ranked[0]
            else:
                # Below threshold - trigger clarification
                return None

        except Exception as e:
            log_template_hit(
                template_id="error",
                confidence=0.0,
                confidence_components={},
                job_id=None,
            )
            return None

    def _keyword_match(
        self,
        ir: Dict[str, Any],
        templates: List[Dict[str, Any]],
        top_k: int,
        min_confidence: float,
    ) -> Optional[TemplateMatch]:
        """
        Fallback keyword matching when embeddings are unavailable.
        """
        if not templates:
            return None

        ir_topic = ir.get("topic", "")
        ir_topic_norm = self._normalize_tag(ir_topic) if ir_topic else ""
        ir_topic_tokens = self._tokenize_phrase(ir_topic)

        ir_emotions = {self._normalize_tag(e) for e in ir.get("emotion_curve", []) if e}

        style = ir.get("style", {}) or {}
        ir_style_values: List[str] = []
        if isinstance(style, dict):
            for key in ("visual", "visual_approach", "visual_style", "color_tone", "lighting"):
                value = style.get(key)
                if value:
                    ir_style_values.append(value)
        elif isinstance(style, str):
            ir_style_values = [style]
        ir_styles = {self._normalize_tag(v) for v in ir_style_values if v}

        candidates: List[TemplateMatch] = []
        for template in templates:
            tags = template.get("tags", {}) or {}
            template_topics = self._coerce_list(tags.get("topic", []))
            template_topic_norms = {self._normalize_tag(t) for t in template_topics if t}
            template_topic_tokens = set()
            for topic in template_topics:
                template_topic_tokens.update(self._tokenize_phrase(topic))

            if ir_topic_norm and ir_topic_norm in template_topic_norms:
                topic_score = 1.0
            elif ir_topic_tokens and template_topic_tokens:
                topic_score = len(ir_topic_tokens & template_topic_tokens) / max(
                    len(ir_topic_tokens), len(template_topic_tokens)
                )
            else:
                topic_score = 0.0

            template_emotions = {
                self._normalize_tag(e) for e in self._coerce_list(tags.get("emotion", [])) if e
            }
            if ir_emotions and template_emotions:
                emotion_score = len(ir_emotions & template_emotions) / max(len(ir_emotions), 1)
            else:
                emotion_score = 0.0

            template_styles = {
                self._normalize_tag(s) for s in self._coerce_list(tags.get("style", [])) if s
            }
            if ir_styles and template_styles:
                style_score = len(ir_styles & template_styles) / max(len(ir_styles), 1)
            else:
                style_score = 0.0

            confidence = (0.6 * topic_score) + (0.2 * emotion_score) + (0.2 * style_score)
            if confidence < min_confidence:
                continue

            candidates.append(
                TemplateMatch(
                    template_id=template["template_id"],
                    version=template["version"],
                    confidence=confidence,
                    confidence_components={
                        "topic": topic_score,
                        "emotion": emotion_score,
                        "style": style_score,
                        "keyword": 1.0,
                    },
                    template=template,
                )
            )

        candidates.sort(key=lambda x: x.confidence, reverse=True)
        return candidates[0] if candidates else None

    def _coerce_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [v for v in value if isinstance(v, str)]
        if isinstance(value, str):
            return [value]
        return []

    def _tokenize_phrase(self, text: str) -> Set[str]:
        if not text:
            return set()
        normalized = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = re.split(r"[_\s]+", normalized)
        return {t for t in tokens if t}

    def _create_query_from_ir(self, ir: Dict[str, Any]) -> str:
        """Create search query from IR"""
        query_parts = []

        topic = ir.get("topic", "")
        if topic:
            query_parts.append(topic)
            if "_" in topic:
                query_parts.append(topic.replace("_", " "))
            elif " " in topic:
                query_parts.append(topic.replace(" ", "_"))
        query_parts.append(ir.get("intent", ""))

        # Add style information
        style = ir.get("style", {})
        query_parts.append(style.get("visual", "") or style.get("visual_approach", "") or style.get("visual_style", ""))
        query_parts.append(style.get("color_tone", ""))
        query_parts.append(style.get("lighting", ""))

        # Add scene information
        scene = ir.get("scene", {})
        query_parts.append(scene.get("location", ""))
        query_parts.append(scene.get("time", ""))

        # Add emotion curve
        emotions = ir.get("emotion_curve", [])
        query_parts.extend(emotions)

        return " ".join([p for p in query_parts if p])

    def _rank_results(
        self,
        ir: Dict[str, Any],
        results: List[tuple],
    ) -> List[TemplateMatch]:
        """
        Rank template matches by combined confidence score

        Confidence = 0.7 * cosine_similarity + 0.3 * jaccard_similarity(tags)

        Args:
            ir: Intermediate Representation
            results: FAISS search results with (doc, score) tuples

        Returns:
            List of ranked TemplateMatch objects
        """
        ranked = []

        for doc, score in results:
            # Get template metadata
            key = doc.metadata.get("key")
            template = self.template_metadata.get(key)

            if not template:
                continue

            # Calculate cosine similarity (normalized to [0, 1])
            # FAISS returns squared L2 distance for normalized vectors:
            # cosine = 1 - (d^2 / 2)
            cosine_sim = 1 - (score / 2)
            cosine_sim = max(0.0, min(1.0, cosine_sim))

            # Calculate Jaccard similarity for tags
            jaccard_sim = self._calculate_jaccard_similarity(ir, template)

            # Combined confidence
            confidence = 0.7 * cosine_sim + 0.3 * jaccard_sim

            match = TemplateMatch(
                template_id=template["template_id"],
                version=template["version"],
                confidence=confidence,
                confidence_components={
                    "cosine": cosine_sim,
                    "jaccard": jaccard_sim,
                },
                template=template,
            )

            ranked.append(match)

        # Sort by confidence descending
        ranked.sort(key=lambda x: x.confidence, reverse=True)

        return ranked

    def _calculate_jaccard_similarity(
        self,
        ir: Dict[str, Any],
        template: Dict[str, Any],
    ) -> float:
        """
        Calculate Jaccard similarity between IR tags and template tags

        Args:
            ir: Intermediate Representation
            template: Template dictionary

        Returns:
            Jaccard similarity [0, 1]
        """
        # Extract IR tags
        ir_tags = set()

        ir_topic = ir.get("topic", "")
        if ir_topic:
            ir_tags.add(self._normalize_tag(ir_topic))

        style = ir.get("style", {})
        style_visual = style.get("visual") or style.get("visual_approach") or style.get("visual_style")
        if style_visual:
            ir_tags.add(self._normalize_tag(style_visual))
        for key in ("color_tone", "lighting"):
            value = style.get(key)
            if value:
                ir_tags.add(self._normalize_tag(value))

        scene = ir.get("scene", {})
        for key in ("location", "time"):
            value = scene.get(key)
            if value:
                ir_tags.add(self._normalize_tag(value))

        ir_emotions = ir.get("emotion_curve", [])
        ir_tags.update([self._normalize_tag(e) for e in ir_emotions if e])

        # Extract template tags
        template_tags_dict = template.get("tags", {})
        template_tags = set()

        for category, tags in template_tags_dict.items():
            if isinstance(tags, list):
                template_tags.update([self._normalize_tag(t) for t in tags if t])
            elif isinstance(tags, str):
                template_tags.add(self._normalize_tag(tags))

        template_emotions = template.get("emotion_curve", []) or []
        template_tags.update([self._normalize_tag(e) for e in template_emotions if e])

        # Calculate Jaccard similarity
        if not ir_tags or not template_tags:
            return 0.0

        intersection = len(ir_tags & template_tags)
        union = len(ir_tags | template_tags)

        return intersection / union if union > 0 else 0.0

    def get_template_by_id(
        self,
        template_id: str,
        version: str,
        db: Session,
    ) -> Optional[Dict[str, Any]]:
        """
        Get template by ID and version

        Args:
            template_id: Template identifier
            version: Template version
            db: Database session

        Returns:
            Template dictionary or None
        """
        template = TemplateDB.get_template(db, template_id, version)
        return template.to_dict() if template else None
