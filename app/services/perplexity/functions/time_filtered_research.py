"""
Time-Filtered Research Function
Searches with specific time constraints (recent vs historical)
Priority: Important - for time-sensitive analysis
"""
from typing import Dict, Any
from app.services.perplexity.perplexity_client import PerplexityClient


async def execute(
    query: str,
    parameters: Dict[str, Any],
    client: PerplexityClient
) -> Dict[str, Any]:
    """
    Execute time-filtered research using Perplexity

    Parameters:
        query: Research question
        parameters: {
            "recency_filter": "day",  # Required: "day", "week", "month", "year"
            "domain_filter": [],  # Optional: Restrict to specific domains
            "return_related_questions": true,  # Optional: Get related questions
            "model": "llama-3.1-sonar-small-128k-online"  # Optional
        }

    Returns:
        {
            "content": "Recent findings...",
            "citations": [{"url": "...", "title": "..."}],
            "related_questions": ["Q1", "Q2"],  # If requested
            "tokens_used": 1500,
            "cost_usd": 0.0003,
            "time_filter": "day"
        }
    """
    recency_filter = parameters.get("recency_filter")
    domain_filter = parameters.get("domain_filter", [])
    return_related = parameters.get("return_related_questions", False)
    model = parameters.get("model", "llama-3.1-sonar-small-128k-online")

    if not recency_filter:
        raise ValueError("recency_filter is required for time-filtered research")

    valid_recency = ["day", "week", "month", "year"]
    if recency_filter not in valid_recency:
        raise ValueError(f"recency_filter must be one of: {valid_recency}")

    response = await client.search(
        query=query,
        model=model,
        search_recency_filter=recency_filter,
        search_domain_filter=domain_filter if domain_filter else None,
        return_citations=True,
        return_related_questions=return_related
    )

    cost = client.calculate_cost(response["usage"], model)

    result = {
        "content": response["content"],
        "citations": response.get("citations", []),
        "model": model,
        "tokens_used": response["usage"].get("total_tokens", 0),
        "cost_usd": cost,
        "time_filter": recency_filter,
        "metadata": {
            "recency_filter": recency_filter,
            "domain_filter": domain_filter,
            "prompt_tokens": response["usage"].get("prompt_tokens", 0),
            "completion_tokens": response["usage"].get("completion_tokens", 0)
        }
    }

    if return_related and "related_questions" in response:
        result["related_questions"] = response["related_questions"]

    return result
