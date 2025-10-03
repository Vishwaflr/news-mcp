"""
Integration tests for geopolitical analysis storage and retrieval
"""

import pytest
import json
from datetime import datetime
from app.services.llm_client import LLMClient

# Mock LLM response for testing storage
MOCK_GEOPOLITICAL_RESPONSE = {
    "overall": {"label": "negative", "score": -0.6, "confidence": 0.85},
    "market": {"bullish": 0.2, "bearish": 0.8, "uncertainty": 0.4, "time_horizon": "short"},
    "urgency": 0.7,
    "impact": {"overall": 0.8, "volatility": 0.6},
    "themes": ["conflict", "sanctions", "energy"],
    "geopolitical": {
        "stability_score": -0.6,
        "economic_impact": -0.5,
        "security_relevance": 0.8,
        "diplomatic_impact": {"global": -0.3, "western": -0.6, "regional": -0.8},
        "impact_beneficiaries": ["UA", "EU", "NATO"],
        "impact_affected": ["RU", "Energy_Markets"],
        "regions_affected": ["Eastern_Europe", "EU"],
        "time_horizon": "immediate",
        "confidence": 0.85,
        "escalation_potential": 0.6,
        "alliance_activation": ["NATO Article 5"],
        "conflict_type": "economic"
    }
}


class TestGeopoliticalStorage:
    """Test storage and retrieval of geopolitical data"""

    def test_validate_and_store_geopolitical_data(self):
        """Test that LLM client correctly validates and formats geopolitical data"""

        # Create mock LLM client (bypass __init__)
        class MockLLM:
            pass

        MockLLM._validate_and_normalize_result = LLMClient._validate_and_normalize_result
        MockLLM._validate_geopolitical = LLMClient._validate_geopolitical
        MockLLM._validate_entities = LLMClient._validate_entities
        MockLLM._get_empty_geopolitical = LLMClient._get_empty_geopolitical

        llm = MockLLM()

        # Validate the mock response
        validated = llm._validate_and_normalize_result(MOCK_GEOPOLITICAL_RESPONSE)

        # Verify structure
        assert "geopolitical" in validated
        assert validated["geopolitical"]["stability_score"] == -0.6
        assert validated["geopolitical"]["economic_impact"] == -0.5
        assert validated["geopolitical"]["security_relevance"] == 0.8

        # Verify diplomatic impact
        assert validated["geopolitical"]["diplomatic_impact"]["global"] == -0.3
        assert validated["geopolitical"]["diplomatic_impact"]["western"] == -0.6
        assert validated["geopolitical"]["diplomatic_impact"]["regional"] == -0.8

        # Verify entities
        assert validated["geopolitical"]["impact_beneficiaries"] == ["UA", "EU", "NATO"]
        assert validated["geopolitical"]["impact_affected"] == ["RU", "Energy_Markets"]

        # Verify enums
        assert validated["geopolitical"]["time_horizon"] == "immediate"
        assert validated["geopolitical"]["conflict_type"] == "economic"

        # Verify confidence and escalation
        assert validated["geopolitical"]["confidence"] == 0.85
        assert validated["geopolitical"]["escalation_potential"] == 0.6

    def test_json_serialization_for_database(self):
        """Test that geopolitical data can be JSON serialized for JSONB storage"""

        class MockLLM:
            pass

        MockLLM._validate_and_normalize_result = LLMClient._validate_and_normalize_result
        MockLLM._validate_geopolitical = LLMClient._validate_geopolitical
        MockLLM._validate_entities = LLMClient._validate_entities
        MockLLM._get_empty_geopolitical = LLMClient._get_empty_geopolitical

        llm = MockLLM()
        validated = llm._validate_and_normalize_result(MOCK_GEOPOLITICAL_RESPONSE)

        # Serialize to JSON (what gets stored in sentiment_json JSONB column)
        json_str = json.dumps(validated, default=str)
        assert json_str is not None
        assert len(json_str) > 0

        # Deserialize and verify
        deserialized = json.loads(json_str)
        assert deserialized["geopolitical"]["stability_score"] == -0.6
        assert deserialized["geopolitical"]["impact_beneficiaries"] == ["UA", "EU", "NATO"]

    def test_storage_without_geopolitical_data(self):
        """Test backward compatibility - analysis without geopolitical data"""

        # Mock response without geopolitical field (old-style analysis)
        old_response = {
            "overall": {"label": "neutral", "score": 0.0, "confidence": 0.5},
            "market": {"bullish": 0.5, "bearish": 0.5, "uncertainty": 0.5, "time_horizon": "medium"},
            "urgency": 0.3,
            "impact": {"overall": 0.4, "volatility": 0.3},
            "themes": []
        }

        class MockLLM:
            pass

        MockLLM._validate_and_normalize_result = LLMClient._validate_and_normalize_result
        MockLLM._validate_geopolitical = LLMClient._validate_geopolitical
        MockLLM._validate_entities = LLMClient._validate_entities
        MockLLM._get_empty_geopolitical = LLMClient._get_empty_geopolitical

        llm = MockLLM()
        validated = llm._validate_and_normalize_result(old_response)

        # Should have geopolitical field with empty values
        assert "geopolitical" in validated
        assert validated["geopolitical"]["stability_score"] == 0.0
        assert validated["geopolitical"]["impact_affected"] == []
        assert validated["geopolitical"]["confidence"] == 0.0

        # Old fields should still work
        assert validated["overall"]["score"] == 0.0
        assert validated["urgency"] == 0.3


class TestGeopoliticalQueries:
    """Test query patterns for geopolitical data (documentation)"""

    def test_query_examples(self):
        """Document example queries for geopolitical data"""

        # These are example queries that would be used in repositories/API
        query_examples = {
            "high_instability": """
                SELECT * FROM items i
                JOIN item_analysis ia ON i.id = ia.item_id
                WHERE (ia.sentiment_json->'geopolitical'->>'stability_score')::float <= -0.5
                ORDER BY (ia.sentiment_json->'geopolitical'->>'stability_score')::float ASC
                LIMIT 10
            """,

            "high_security_relevance": """
                SELECT * FROM items i
                JOIN item_analysis ia ON i.id = ia.item_id
                WHERE (ia.sentiment_json->'geopolitical'->>'security_relevance')::float >= 0.7
                ORDER BY (ia.sentiment_json->'geopolitical'->>'security_relevance')::float DESC
                LIMIT 10
            """,

            "articles_affecting_russia": """
                SELECT * FROM items i
                JOIN item_analysis ia ON i.id = ia.item_id
                WHERE ia.sentiment_json->'geopolitical'->'impact_affected' ? 'RU'
                LIMIT 10
            """,

            "articles_affecting_russia_or_china": """
                SELECT * FROM items i
                JOIN item_analysis ia ON i.id = ia.item_id
                WHERE ia.sentiment_json->'geopolitical'->'impact_affected' ?| array['RU', 'CN']
                LIMIT 10
            """,

            "eastern_europe_news": """
                SELECT * FROM items i
                JOIN item_analysis ia ON i.id = ia.item_id
                WHERE ia.sentiment_json->'geopolitical'->'regions_affected' ? 'Eastern_Europe'
                LIMIT 10
            """,

            "interstate_war_articles": """
                SELECT * FROM items i
                JOIN item_analysis ia ON i.id = ia.item_id
                WHERE ia.sentiment_json->'geopolitical'->>'conflict_type' = 'interstate_war'
                LIMIT 10
            """,

            "immediate_escalation_risk": """
                SELECT * FROM items i
                JOIN item_analysis ia ON i.id = ia.item_id
                WHERE ia.sentiment_json->'geopolitical'->>'time_horizon' = 'immediate'
                  AND (ia.sentiment_json->'geopolitical'->>'escalation_potential')::float >= 0.6
                ORDER BY (ia.sentiment_json->'geopolitical'->>'escalation_potential')::float DESC
                LIMIT 10
            """
        }

        # Verify query structure (documentation test)
        assert "high_instability" in query_examples
        assert "articles_affecting_russia" in query_examples
        assert "immediate_escalation_risk" in query_examples

        # This test serves as documentation for how to query geopolitical data
        print("\n📚 Example Geopolitical Queries:")
        for name, query in query_examples.items():
            print(f"\n{name}:")
            print(query.strip())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
