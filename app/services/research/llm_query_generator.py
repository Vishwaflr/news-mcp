"""
LLM Query Generator Service
Generates research queries using LLM based on filtered articles
"""
from typing import List, Dict, Any
from openai import OpenAI
from app.core.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)


class LLMQueryGeneratorService:
    """Service for generating research queries using LLM"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.default_model = "gpt-4o-mini"

    def generate_queries(
        self,
        articles: List[Dict[str, Any]],
        user_prompt: str,
        model: str = None
    ) -> Dict[str, Any]:
        """
        Generate research queries based on articles and user prompt

        Args:
            articles: List of article dictionaries
            user_prompt: User's custom prompt
            model: LLM model to use (defaults to gpt-4o-mini)

        Returns:
            Dictionary with generated queries and metadata
        """
        try:
            model = model or self.default_model

            # Build context from articles
            articles_context = self._build_articles_context(articles)

            # Build system prompt
            system_prompt = """You are a research assistant specialized in analyzing news articles and generating insightful research questions.

Your task is to:
1. Carefully read and analyze the provided news articles
2. Identify key themes, actors, and geopolitical/economic implications
3. Generate focused, actionable research questions based on the user's request

Generate questions that:
- Are specific and actionable
- Go beyond surface-level information
- Explore cause-and-effect relationships
- Consider multiple perspectives
- Help understand broader context and implications

Format your response as a numbered list of research questions."""

            # Build user message
            user_message = f"""Here are the news articles to analyze:

{articles_context}

---

User's request:
{user_prompt}

Please generate research questions based on these articles."""

            # Call LLM
            logger.info(f"Calling LLM {model} with {len(articles)} articles")
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            generated_queries = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            # Parse queries into list
            queries_list = self._parse_queries(generated_queries)

            logger.info(f"LLM query generation successful: {tokens_used} tokens used, {len(queries_list)} queries extracted")

            return {
                "ok": True,
                "generated_queries": generated_queries,
                "queries_list": queries_list,
                "metadata": {
                    "model": model,
                    "articles_count": len(articles),
                    "tokens_used": tokens_used,
                    "finish_reason": response.choices[0].finish_reason
                }
            }

        except Exception as e:
            logger.error(f"Error generating queries with LLM: {e}")
            return {
                "ok": False,
                "error": str(e),
                "generated_queries": None
            }

    def _build_articles_context(self, articles: List[Dict[str, Any]]) -> str:
        """Build formatted context from articles"""
        context_parts = []

        for idx, article in enumerate(articles, 1):
            context = f"""Article {idx}:
Title: {article.get('title', 'N/A')}
Published: {article.get('published', 'N/A')}
Feed: {article.get('feed_name', 'N/A')}
Category: {article.get('category', 'N/A')}
Actors: {article.get('semantic_tags', {}).get('actor', 'N/A')}
Theme: {article.get('semantic_tags', {}).get('theme', 'N/A')}
Region: {article.get('semantic_tags', {}).get('region', 'N/A')}
Sentiment: {article.get('sentiment', 'N/A')}
Impact: {article.get('impact', {}).get('overall', 0.0) if isinstance(article.get('impact'), dict) else article.get('impact', 0.0)}
"""

            # Add description if available
            description = article.get('description', '').strip()
            if description:
                # Truncate long descriptions
                if len(description) > 500:
                    description = description[:500] + "..."
                context += f"Summary: {description}\n"

            context_parts.append(context)

        return "\n".join(context_parts)

    def _parse_queries(self, generated_text: str) -> List[str]:
        """
        Parse numbered list of queries from generated text

        Handles formats like:
        1. Query one
        2. Query two
        """
        queries = []
        lines = generated_text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match numbered queries: "1. ", "2. ", etc.
            import re
            match = re.match(r'^\d+\.\s+(.+)$', line)
            if match:
                query = match.group(1).strip()
                queries.append(query)

        # Fallback: if no numbered queries found, return whole text as single query
        if not queries:
            queries = [generated_text.strip()]

        return queries
