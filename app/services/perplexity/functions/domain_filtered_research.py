"""
Domain-Filtered Research Function
Searches only within specified trusted domains
Priority: Highest - ensures only verified sources
"""
from typing import Dict, Any, List
from app.services.perplexity.perplexity_client import PerplexityClient


async def execute(
    query: str,
    parameters: Dict[str, Any],
    client: PerplexityClient
) -> Dict[str, Any]:
    """
    Execute domain-filtered research using Perplexity

    Parameters:
        query: Research question
        parameters: {
            "domain_filter": ["reuters.com", "apnews.com", ".gov"],  # Trusted domains
            "recency_filter": "day",  # "day", "week", "month", "year"
            "model": "llama-3.1-sonar-small-128k-online"  # Optional
        }

    Returns:
        {
            "content": "Research findings...",
            "citations": [{"url": "...", "title": "..."}],
            "tokens_used": 1500,
            "cost_usd": 0.0003
        }
    """
    domain_filter = parameters.get("domain_filter", [])
    recency = parameters.get("recency_filter", "month")
    model = parameters.get("model", "sonar")

    if not domain_filter:
        raise ValueError("domain_filter is required for domain-filtered research")

    response = await client.search(
        query=query,
        model=model,
        search_domain_filter=domain_filter,
        search_recency_filter=recency
    )

    cost = client.calculate_cost(response["usage"], model)

    return {
        "content": response["content"],
        "citations": response.get("citations", []),
        "model": model,
        "tokens_used": response["usage"].get("total_tokens", 0),
        "cost_usd": cost,
        "metadata": {
            "domain_filter": domain_filter,
            "recency_filter": recency,
            "prompt_tokens": response["usage"].get("prompt_tokens", 0),
            "completion_tokens": response["usage"].get("completion_tokens", 0)
        }
    }
