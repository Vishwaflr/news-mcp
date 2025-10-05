"""
Domain-Filtered Research Function
Searches only within specified trusted domains
Priority: Highest - ensures only verified sources
"""
from typing import Dict, Any, List
from app.services.perplexity.perplexity_client import PerplexityClient


# Schema definition for dynamic form generation
SCHEMA = {
    "name": "domain_filtered_research",
    "display_name": "Domain-Filtered Research",
    "description": "Search only within specified trusted domains (e.g., reuters.com, .gov)",
    "icon": "bi-funnel",
    "parameters": [
        {
            "name": "domain_filter",
            "display_name": "Trusted Domains",
            "type": "array",
            "item_type": "string",
            "required": True,
            "description": "List of domains to restrict search results",
            "placeholder": "reuters.com\napnews.com\n.gov\n.edu",
            "help_text": "Enter one domain per line. Use .gov, .edu for top-level domains.",
            "validation": {
                "min_items": 1,
                "pattern": r"^[a-zA-Z0-9.-]+$"
            }
        },
        {
            "name": "recency_filter",
            "display_name": "Time Range",
            "type": "enum",
            "options": [
                {"value": "day", "label": "Last 24 hours"},
                {"value": "week", "label": "Last week"},
                {"value": "month", "label": "Last month"},
                {"value": "year", "label": "Last year"}
            ],
            "default": "month",
            "required": False,
            "description": "How recent the content should be"
        }
    ]
}


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
