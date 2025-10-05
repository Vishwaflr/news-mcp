"""
Analytics Research Function
Executes research with detailed cost/performance tracking
Priority: Useful - for monitoring and optimization
"""
from typing import Dict, Any
from datetime import datetime
from app.services.perplexity.perplexity_client import PerplexityClient


# Schema definition for dynamic form generation
SCHEMA = {
    "name": "analytics_research",
    "display_name": "Analytics Research",
    "description": "Research with comprehensive performance and cost tracking",
    "icon": "bi-graph-up",
    "parameters": [
        {
            "name": "track_performance",
            "display_name": "Track Performance Metrics",
            "type": "boolean",
            "default": True,
            "required": False,
            "description": "Include execution time and performance data"
        },
        {
            "name": "include_token_breakdown",
            "display_name": "Include Token Breakdown",
            "type": "boolean",
            "default": True,
            "required": False,
            "description": "Show detailed prompt/completion token counts"
        },
        {
            "name": "domain_filter",
            "display_name": "Domain Filter (Optional)",
            "type": "array",
            "item_type": "string",
            "required": False,
            "description": "Optionally restrict to specific domains",
            "placeholder": "reuters.com\napnews.com"
        },
        {
            "name": "recency_filter",
            "display_name": "Time Range (Optional)",
            "type": "enum",
            "options": [
                {"value": "day", "label": "Last 24 hours"},
                {"value": "week", "label": "Last week"},
                {"value": "month", "label": "Last month"},
                {"value": "year", "label": "Last year"}
            ],
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
    Execute research with comprehensive analytics tracking

    Parameters:
        query: Research question
        parameters: {
            "track_performance": true,  # Track timing metrics
            "include_token_breakdown": true,  # Detailed token usage
            "model": "llama-3.1-sonar-small-128k-online",  # Optional
            "domain_filter": [],  # Optional
            "recency_filter": "month"  # Optional
        }

    Returns:
        {
            "content": "Research findings...",
            "citations": [...],
            "analytics": {
                "total_tokens": 1500,
                "prompt_tokens": 100,
                "completion_tokens": 1400,
                "cost_usd": 0.0003,
                "cost_per_token": 0.0000002,
                "execution_time_seconds": 3.45,
                "characters_generated": 2800,
                "citations_count": 5,
                "model_used": "llama-3.1-sonar-small-128k-online",
                "timestamp": "2025-10-05T12:00:00Z"
            }
        }
    """
    track_performance = parameters.get("track_performance", True)
    include_token_breakdown = parameters.get("include_token_breakdown", True)
    model = parameters.get("model", "sonar")
    domain_filter = parameters.get("domain_filter", [])
    recency_filter = parameters.get("recency_filter")

    start_time = datetime.utcnow()

    response = await client.search(
        query=query,
        model=model,
        search_domain_filter=domain_filter if domain_filter else None,
        search_recency_filter=recency_filter
    )

    end_time = datetime.utcnow()
    execution_time = (end_time - start_time).total_seconds()

    usage = response["usage"]
    cost = client.calculate_cost(usage, model)
    total_tokens = usage.get("total_tokens", 0)
    content = response["content"]
    citations = response.get("citations", [])

    # Build analytics
    analytics = {
        "total_tokens": total_tokens,
        "cost_usd": cost,
        "cost_per_token": round(cost / total_tokens, 10) if total_tokens > 0 else 0,
        "characters_generated": len(content),
        "citations_count": len(citations),
        "model_used": model,
        "timestamp": end_time.isoformat()
    }

    if track_performance:
        analytics["execution_time_seconds"] = round(execution_time, 2)

    if include_token_breakdown:
        analytics["prompt_tokens"] = usage.get("prompt_tokens", 0)
        analytics["completion_tokens"] = usage.get("completion_tokens", 0)

    return {
        "content": content,
        "citations": citations,
        "analytics": analytics,
        "metadata": {
            "model": model,
            "domain_filter": domain_filter,
            "recency_filter": recency_filter
        }
    }
