"""
Perplexity API Client
HTTP client for Perplexity API with rate limiting and error handling
"""
import os
import asyncio
from typing import Dict, Any, List, Optional
import httpx
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class PerplexityClient:
    """Client for Perplexity API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not found in environment variables")

        self.base_url = "https://api.perplexity.ai"
        self.timeout = 60.0

    async def search(
        self,
        query: str,
        model: str = "sonar",
        search_domain_filter: Optional[List[str]] = None,
        search_recency_filter: Optional[str] = None,
        return_images: bool = False,
        return_related_questions: bool = False,
        return_citations: bool = True,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a search query using Perplexity API

        Args:
            query: The search query
            model: Perplexity model to use
            search_domain_filter: List of domains to filter results (e.g., ["reuters.com", ".gov"])
            search_recency_filter: Time filter ("day", "week", "month", "year")
            return_images: Whether to return images
            return_related_questions: Whether to return related questions
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            API response with content, citations, and usage stats
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Be precise and concise. Provide factual information with sources."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": temperature
        }

        # Optional parameters
        if return_citations:
            payload["return_citations"] = return_citations

        if return_images:
            payload["return_images"] = return_images

        if return_related_questions:
            payload["return_related_questions"] = return_related_questions

        if search_domain_filter:
            payload["search_domain_filter"] = search_domain_filter

        if search_recency_filter:
            payload["search_recency_filter"] = search_recency_filter

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                # Extract content and citations
                content = data["choices"][0]["message"]["content"]
                citations = data.get("citations", [])
                usage = data.get("usage", {})

                result = {
                    "content": content,
                    "citations": citations,
                    "usage": usage,
                    "model": model
                }

                if return_images and "images" in data:
                    result["images"] = data["images"]

                if return_related_questions and "related_questions" in data:
                    result["related_questions"] = data["related_questions"]

                logger.info(f"Perplexity search completed: {usage.get('total_tokens', 0)} tokens used")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Perplexity API HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Perplexity API error: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error("Perplexity API timeout")
            raise Exception("Perplexity API timeout")
        except Exception as e:
            logger.error(f"Perplexity API unexpected error: {e}")
            raise

    async def structured_search(
        self,
        query: str,
        response_format: Dict[str, Any],
        model: str = "sonar",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a search with structured JSON output

        Args:
            query: The search query
            response_format: JSON schema for structured output
            model: Perplexity model to use
            **kwargs: Additional parameters passed to search()

        Returns:
            Structured JSON response matching the schema
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise assistant that returns structured JSON responses."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "response_format": response_format,
            **kwargs
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Perplexity structured search completed")
                return data

        except Exception as e:
            logger.error(f"Perplexity structured search error: {e}")
            raise

    def calculate_cost(self, usage: Dict[str, Any], model: str) -> float:
        """
        Calculate cost based on token usage

        Pricing (as of 2025-10, from https://docs.perplexity.ai/pricing):
        Token Pricing (Input/Output per 1M tokens):
        - sonar: $1/$1
        - sonar-pro: $3/$15
        - sonar-reasoning: $1/$5
        - sonar-reasoning-pro: $2/$8
        - sonar-deep-research: $2/$8 + $2 citations + $5/1K queries + $3 reasoning

        Note: Simplified calculation using average of input/output for now
        """
        # Simplified pricing (average of input/output per 1M tokens)
        pricing = {
            "sonar": 1.0,  # ($1 + $1) / 2
            "sonar-pro": 9.0,  # ($3 + $15) / 2
            "sonar-reasoning": 3.0,  # ($1 + $5) / 2
            "sonar-reasoning-pro": 5.0,  # ($2 + $8) / 2
            "sonar-deep-research": 5.0  # ($2 + $8) / 2 base (additional costs not included)
        }

        cost_per_1m = pricing.get(model, 1.0)
        total_tokens = usage.get("total_tokens", 0)

        cost = (total_tokens / 1_000_000) * cost_per_1m
        return round(cost, 6)
