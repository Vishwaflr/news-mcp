import pytest
import os
from unittest.mock import patch, MagicMock
from app.services.llm_client import LLMClient

# Mock OpenAI API key for tests
os.environ['OPENAI_API_KEY'] = 'test-key-for-tests'

class TestLLMParsing:
    def test_validate_complete_result(self):
        """Test validation of complete LLM result"""
        client = LLMClient()

        valid_result = {
            "overall": {"label": "positive", "score": 0.8, "confidence": 0.9},
            "market": {"bullish": 0.7, "bearish": 0.2, "uncertainty": 0.1, "time_horizon": "short"},
            "urgency": 0.6,
            "impact": {"overall": 0.8, "volatility": 0.4},
            "themes": ["crypto", "bitcoin"]
        }

        normalized = client._validate_and_normalize_result(valid_result)

        assert normalized["overall"]["label"] == "positive"
        assert 0 <= normalized["overall"]["score"] <= 1
        assert 0 <= normalized["urgency"] <= 1
        assert len(normalized["themes"]) <= 6

    def test_validate_incomplete_result(self):
        """Test validation with missing fields falls back to defaults"""
        client = LLMClient()

        incomplete_result = {
            "overall": {"label": "positive"},
            "impact": {"overall": 0.5}
        }

        normalized = client._validate_and_normalize_result(incomplete_result)

        # Should have defaults
        assert "score" in normalized["overall"]
        assert "confidence" in normalized["overall"]
        assert "market" in normalized
        assert normalized["market"]["time_horizon"] in ["short", "medium", "long"]
        assert "urgency" in normalized

    def test_validate_malformed_result(self):
        """Test validation with completely malformed data"""
        client = LLMClient()

        malformed_result = {"invalid": "data"}

        normalized = client._validate_and_normalize_result(malformed_result)

        # Should return fallback
        assert normalized["overall"]["label"] == "neutral"
        assert normalized["overall"]["score"] == 0.0
        assert normalized["urgency"] == 0.0

    def test_get_fallback_result(self):
        """Test fallback result structure"""
        client = LLMClient()

        fallback = client._get_fallback_result()

        assert fallback["overall"]["label"] == "neutral"
        assert fallback["overall"]["score"] == 0.0
        assert fallback["overall"]["confidence"] == 0.0
        assert fallback["impact"]["overall"] == 0.0
        assert fallback["themes"] == []

    @patch('app.services.llm_client.OpenAI')
    def test_json_parse_error_handling(self, mock_openai):
        """Test handling of JSON parse errors"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Invalid JSON {{"
        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient()
        result = client.classify("Test title", "Test summary")

        # Should return fallback
        assert result["overall"]["label"] == "neutral"

    @patch('app.services.llm_client.OpenAI')
    def test_api_error_handling(self, mock_openai):
        """Test handling of API errors"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock API exception
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        client = LLMClient()
        result = client.classify("Test title", "Test summary")

        # Should return fallback
        assert result["overall"]["label"] == "neutral"