"""
Perplexity API Client Service
Executes research queries using Perplexity's search-enhanced LLM
"""
from typing import Dict, Any, List
from openai import OpenAI
from app.core.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)


class PerplexityClientService:
    """Service for executing research queries with Perplexity API"""

    def __init__(self):
        # Perplexity API uses OpenAI-compatible interface
        self.client = OpenAI(
            api_key=settings.perplexity_api_key,
            base_url="https://api.perplexity.ai"
        )
        # Perplexity current models (2025): sonar, sonar-pro, sonar-reasoning, etc.
        self.default_model = "sonar"

    def execute_research(
        self,
        queries: List[str],
        model: str = None
    ) -> Dict[str, Any]:
        """
        Execute research queries using Perplexity

        Args:
            queries: List of research questions to execute
            model: Perplexity model to use (defaults to sonar-small-128k-online)

        Returns:
            Dictionary with research results and metadata
        """
        try:
            model = model or self.default_model

            # Combine queries into a single research prompt
            combined_prompt = self._build_research_prompt(queries)

            logger.info(f"Executing research with Perplexity {model} ({len(queries)} queries)")

            # Call Perplexity API
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a research assistant. Provide comprehensive, well-sourced answers to research questions. Include specific facts, dates, and cite sources when possible."
                    },
                    {
                        "role": "user",
                        "content": combined_prompt
                    }
                ],
                temperature=0.2,  # Lower temperature for factual research
                max_tokens=4000
            )

            research_results = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            logger.info(f"Perplexity research successful: {tokens_used} tokens used")

            # Extract citations if available (Perplexity includes inline citations)
            citations = self._extract_citations(research_results)

            return {
                "ok": True,
                "research_results": research_results,
                "citations": citations,
                "metadata": {
                    "model": model,
                    "queries_count": len(queries),
                    "tokens_used": tokens_used,
                    "finish_reason": response.choices[0].finish_reason
                }
            }

        except Exception as e:
            logger.error(f"Error executing Perplexity research: {e}")
            return {
                "ok": False,
                "error": str(e),
                "research_results": None,
                "citations": []
            }

    def _build_research_prompt(self, queries: List[str]) -> str:
        """Build combined research prompt from queries"""
        prompt = "Please research and answer the following questions:\n\n"

        for idx, query in enumerate(queries, 1):
            prompt += f"{idx}. {query}\n\n"

        prompt += "\nProvide detailed, well-sourced answers with specific facts and citations."

        return prompt

    def _extract_citations(self, content: str) -> List[Dict[str, str]]:
        """
        Extract citations from Perplexity response

        Perplexity includes inline citations like [1], [2], etc.
        This is a basic extraction - can be enhanced later.
        """
        citations = []

        # Look for citation patterns [1], [2], etc.
        # Perplexity sometimes includes source URLs at the end
        # This is a placeholder for future enhancement

        # For now, return empty list - citations are inline in the text
        return citations
