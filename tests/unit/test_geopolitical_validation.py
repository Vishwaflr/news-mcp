"""
Unit tests for geopolitical analysis validation
"""

import pytest
from app.domain.analysis.schema import (
    GeopoliticalPayload,
    DiplomaticImpact,
    AnalysisResult,
    SentimentPayload,
    ImpactPayload,
    Overall,
    Market
)

class TestGeopoliticalPayloadValidation:
    """Test GeopoliticalPayload Pydantic validation"""

    def test_valid_geopolitical_payload(self):
        """Test valid geopolitical data passes validation"""
        geo = GeopoliticalPayload(
            stability_score=-0.6,
            economic_impact=-0.5,
            security_relevance=0.8,
            diplomatic_impact=DiplomaticImpact(
                global_impact=-0.3,
                western=-0.6,
                regional=-0.8
            ),
            impact_beneficiaries=["UA", "EU", "NATO"],
            impact_affected=["RU", "Energy_Markets"],
            regions_affected=["Eastern_Europe", "EU"],
            time_horizon="immediate",
            confidence=0.85,
            escalation_potential=0.6,
            alliance_activation=["NATO Article 5"],
            conflict_type="economic"
        )

        assert geo.stability_score == -0.6
        assert geo.economic_impact == -0.5
        assert geo.security_relevance == 0.8
        assert geo.diplomatic_impact.global_impact == -0.3
        assert len(geo.impact_beneficiaries) == 3
        assert geo.time_horizon == "immediate"
        assert geo.conflict_type == "economic"

    def test_max_three_beneficiaries(self):
        """Test that impact_beneficiaries rejects more than 3 items"""
        # Pydantic max_items validation happens BEFORE custom validators
        # So > 3 items should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            GeopoliticalPayload(
                stability_score=0.0,
                economic_impact=0.0,
                security_relevance=0.0,
                diplomatic_impact=DiplomaticImpact(global_impact=0.0, western=0.0, regional=0.0),
                impact_beneficiaries=["UA", "EU", "NATO", "US"],  # 4 items - should fail
                impact_affected=[],
                regions_affected=[],
                time_horizon="short_term",
                confidence=0.5,
                escalation_potential=0.0,
                alliance_activation=[],
                conflict_type="diplomatic"
            )

    def test_score_range_validation(self):
        """Test that scores are validated within ranges"""
        # Should raise ValidationError for out-of-range scores
        with pytest.raises(Exception):  # Pydantic ValidationError
            GeopoliticalPayload(
                stability_score=2.0,  # Invalid: > 1.0
                economic_impact=0.0,
                security_relevance=0.0,
                diplomatic_impact=DiplomaticImpact(global_impact=0.0, western=0.0, regional=0.0),
                impact_beneficiaries=[],
                impact_affected=[],
                regions_affected=[],
                time_horizon="short_term",
                confidence=0.5,
                escalation_potential=0.0,
                alliance_activation=[],
                conflict_type="diplomatic"
            )

    def test_invalid_time_horizon(self):
        """Test that invalid time_horizon is rejected"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            GeopoliticalPayload(
                stability_score=0.0,
                economic_impact=0.0,
                security_relevance=0.0,
                diplomatic_impact=DiplomaticImpact(global_impact=0.0, western=0.0, regional=0.0),
                impact_beneficiaries=[],
                impact_affected=[],
                regions_affected=[],
                time_horizon="invalid_horizon",  # Invalid
                confidence=0.5,
                escalation_potential=0.0,
                alliance_activation=[],
                conflict_type="diplomatic"
            )

    def test_invalid_conflict_type(self):
        """Test that invalid conflict_type is rejected"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            GeopoliticalPayload(
                stability_score=0.0,
                economic_impact=0.0,
                security_relevance=0.0,
                diplomatic_impact=DiplomaticImpact(global_impact=0.0, western=0.0, regional=0.0),
                impact_beneficiaries=[],
                impact_affected=[],
                regions_affected=[],
                time_horizon="short_term",
                confidence=0.5,
                escalation_potential=0.0,
                alliance_activation=[],
                conflict_type="cyber_warfare"  # Invalid
            )


class TestAnalysisResultWithGeopolitical:
    """Test AnalysisResult with optional geopolitical field"""

    def test_analysis_result_with_geopolitical(self):
        """Test AnalysisResult accepts geopolitical payload"""
        result = AnalysisResult(
            sentiment=SentimentPayload(
                overall=Overall(label="positive", score=0.7, confidence=0.8),
                market=Market(bullish=0.8, bearish=0.2, uncertainty=0.3, time_horizon="medium"),
                urgency=0.5,
                themes=["tech", "ai"]
            ),
            impact=ImpactPayload(overall=0.6, volatility=0.4),
            geopolitical=GeopoliticalPayload(
                stability_score=-0.3,
                economic_impact=-0.2,
                security_relevance=0.5,
                diplomatic_impact=DiplomaticImpact(global_impact=-0.1, western=-0.2, regional=-0.3),
                impact_beneficiaries=["US", "EU"],
                impact_affected=["CN"],
                regions_affected=["Asia_Pacific"],
                time_horizon="short_term",
                confidence=0.7,
                escalation_potential=0.3,
                alliance_activation=[],
                conflict_type="economic"
            ),
            model_tag="gpt-4.1-nano"
        )

        assert result.sentiment.overall.score == 0.7
        assert result.geopolitical.stability_score == -0.3
        assert result.model_tag == "gpt-4.1-nano"

    def test_analysis_result_without_geopolitical(self):
        """Test AnalysisResult works without geopolitical (backward compatibility)"""
        result = AnalysisResult(
            sentiment=SentimentPayload(
                overall=Overall(label="neutral", score=0.0, confidence=0.5),
                market=Market(bullish=0.5, bearish=0.5, uncertainty=0.5, time_horizon="medium"),
                urgency=0.3,
                themes=[]
            ),
            impact=ImpactPayload(overall=0.4, volatility=0.3),
            model_tag="gpt-4.1-nano"
        )

        assert result.sentiment.overall.score == 0.0
        assert result.geopolitical is None  # Optional field
        assert result.model_tag == "gpt-4.1-nano"


class TestLLMClientValidation:
    """Test LLM client validation functions"""

    def test_validate_geopolitical_with_valid_data(self):
        """Test _validate_geopolitical with valid data"""
        from app.services.llm_client import LLMClient

        # Create mock instance
        class MockLLM:
            pass
        MockLLM._validate_geopolitical = LLMClient._validate_geopolitical
        MockLLM._validate_entities = LLMClient._validate_entities
        MockLLM._get_empty_geopolitical = LLMClient._get_empty_geopolitical

        llm = MockLLM()

        test_data = {
            "stability_score": -0.6,
            "economic_impact": -0.5,
            "security_relevance": 0.8,
            "diplomatic_impact": {"global": -0.3, "western": -0.6, "regional": -0.8},
            "impact_beneficiaries": ["UA", "EU", "NATO"],
            "impact_affected": ["RU"],
            "regions_affected": ["Eastern_Europe"],
            "time_horizon": "immediate",
            "confidence": 0.85,
            "escalation_potential": 0.6,
            "alliance_activation": ["NATO Article 5"],
            "conflict_type": "economic"
        }

        result = llm._validate_geopolitical(test_data)

        assert result["stability_score"] == -0.6
        assert result["economic_impact"] == -0.5
        assert result["security_relevance"] == 0.8
        assert result["diplomatic_impact"]["global"] == -0.3
        assert len(result["impact_beneficiaries"]) == 3
        assert result["time_horizon"] == "immediate"
        assert result["conflict_type"] == "economic"

    def test_validate_geopolitical_trims_entities(self):
        """Test that entity arrays are trimmed to max 3"""
        from app.services.llm_client import LLMClient

        class MockLLM:
            pass
        MockLLM._validate_geopolitical = LLMClient._validate_geopolitical
        MockLLM._validate_entities = LLMClient._validate_entities
        MockLLM._get_empty_geopolitical = LLMClient._get_empty_geopolitical

        llm = MockLLM()

        test_data = {
            "stability_score": 0.0,
            "economic_impact": 0.0,
            "security_relevance": 0.0,
            "diplomatic_impact": {"global": 0.0, "western": 0.0, "regional": 0.0},
            "impact_beneficiaries": ["UA", "EU", "NATO", "US", "UK"],  # 5 items
            "impact_affected": ["RU", "CN", "IR", "KP"],  # 4 items
            "regions_affected": [],
            "time_horizon": "short_term",
            "confidence": 0.5,
            "escalation_potential": 0.0,
            "alliance_activation": [],
            "conflict_type": "diplomatic"
        }

        result = llm._validate_geopolitical(test_data)

        assert len(result["impact_beneficiaries"]) == 3
        assert len(result["impact_affected"]) == 3

    def test_validate_geopolitical_handles_invalid_enum(self):
        """Test that invalid enums are corrected to defaults"""
        from app.services.llm_client import LLMClient

        class MockLLM:
            pass
        MockLLM._validate_geopolitical = LLMClient._validate_geopolitical
        MockLLM._validate_entities = LLMClient._validate_entities
        MockLLM._get_empty_geopolitical = LLMClient._get_empty_geopolitical

        llm = MockLLM()

        test_data = {
            "stability_score": 0.0,
            "economic_impact": 0.0,
            "security_relevance": 0.0,
            "diplomatic_impact": {"global": 0.0, "western": 0.0, "regional": 0.0},
            "impact_beneficiaries": [],
            "impact_affected": [],
            "regions_affected": [],
            "time_horizon": "invalid_horizon",  # Invalid
            "confidence": 0.5,
            "escalation_potential": 0.0,
            "alliance_activation": [],
            "conflict_type": "cyber_attack"  # Invalid
        }

        result = llm._validate_geopolitical(test_data)

        # Should fall back to defaults
        assert result["time_horizon"] == "short_term"
        assert result["conflict_type"] == "diplomatic"

    def test_get_empty_geopolitical(self):
        """Test empty geopolitical structure"""
        from app.services.llm_client import LLMClient

        class MockLLM:
            pass
        MockLLM._get_empty_geopolitical = LLMClient._get_empty_geopolitical

        llm = MockLLM()
        empty = llm._get_empty_geopolitical()

        assert empty["stability_score"] == 0.0
        assert empty["economic_impact"] == 0.0
        assert empty["security_relevance"] == 0.0
        assert empty["diplomatic_impact"]["global"] == 0.0
        assert empty["impact_beneficiaries"] == []
        assert empty["impact_affected"] == []
        assert empty["regions_affected"] == []
        assert empty["confidence"] == 0.0
        assert empty["escalation_potential"] == 0.0
