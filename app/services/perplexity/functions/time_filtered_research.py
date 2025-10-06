"""
Time-Filtered Research Function
Searches with specific time constraints using date filters (better for citations)
Priority: Important - for time-sensitive analysis

NOTE: Uses search_after_date_filter instead of search_recency_filter
to improve citation availability while maintaining time constraints.
"""
from typing import Dict, Any
from datetime import datetime, timedelta
from app.services.perplexity.perplexity_client import PerplexityClient


# Schema definition for dynamic form generation
SCHEMA = {
    "name": "time_filtered_research",
    "display_name": "Time-Filtered Research",
    "description": "Focus on recent content with improved citation support",
    "icon": "bi-clock-history",
    "parameters": [
        {
            "name": "timeframe_days",
            "display_name": "Timeframe (Days)",
            "type": "enum",
            "options": [
                {"value": "1", "label": "Last 24 hours"},
                {"value": "7", "label": "Last 7 days"},
                {"value": "30", "label": "Last 30 days"},
                {"value": "365", "label": "Last year"}
            ],
            "required": True,
            "description": "How many days back to search",
            "default": "7"
        },
        {
            "name": "domain_filter",
            "display_name": "Domain Filter (Optional)",
            "type": "array",
            "item_type": "string",
            "required": False,
            "description": "Optionally restrict to specific domains (max 20)",
            "placeholder": "reuters.com\napnews.com\nbbc.com\naljazeera.com\ndw.com\nfrance24.com\ntheguardian.com\nwashingtonpost.com\nnytimes.com\ncnn.com\nbloomberg.com\nft.com\npolitico.com\nforeignpolicy.com\neuobserver.com\nrferl.org\ndefensenews.com\neuronews.com\nosce.org\ntheconversation.com",
            "help_text": "Leave empty to search all sources, or enter up to 20 domains (one per line).",
            "validation": {
                "max_items": 20,
                "pattern": r"^[a-zA-Z0-9.-]+$"
            }
        },
        {
            "name": "return_related_questions",
            "display_name": "Include Related Questions",
            "type": "boolean",
            "default": False,
            "required": False,
            "description": "Get suggested follow-up questions"
        }
    ]
}


async def execute(
    query: str,
    parameters: Dict[str, Any],
    client: PerplexityClient
) -> Dict[str, Any]:
    """
    Execute time-filtered research using date filters (better citation support)

    Parameters:
        query: Research question (automatically enhanced with "find sources" for better citations)
        parameters: {
            "timeframe_days": "7",  # Required: Number of days (1, 7, 30, 365)
            "domain_filter": [],  # Optional: Restrict to specific domains
            "return_related_questions": true,  # Optional: Get related questions
            "model": "sonar"  # Optional
        }

    Returns:
        {
            "content": "Recent findings...",
            "citations": [{"url": "...", "title": "..."}],
            "related_questions": ["Q1", "Q2"],  # If requested
            "tokens_used": 1500,
            "cost_usd": 0.0003,
            "timeframe_days": 7,
            "search_after_date": "10/01/2025"
        }
    """
    timeframe_days = parameters.get("timeframe_days")
    domain_filter = parameters.get("domain_filter", [])
    return_related = parameters.get("return_related_questions", False)
    model = parameters.get("model", "sonar")

    if not timeframe_days:
        raise ValueError("timeframe_days is required for time-filtered research")

    # Convert timeframe to date filter
    try:
        days = int(timeframe_days)
    except ValueError:
        raise ValueError(f"timeframe_days must be a number, got: {timeframe_days}")

    # Calculate date filter (format: MM/DD/YYYY as per Perplexity API docs)
    cutoff_date = datetime.now() - timedelta(days=days)
    date_filter = cutoff_date.strftime("%m/%d/%Y")

    # Enhance query with citation-friendly phrasing
    enhanced_query = f"{query} - find recent sources and cite references"

    response = await client.search(
        query=enhanced_query,
        model=model,
        search_after_date_filter=date_filter,  # Use date filter instead of recency_filter
        search_domain_filter=domain_filter if domain_filter else None,
        return_related_questions=return_related
    )

    cost = client.calculate_cost(response["usage"], model)

    result = {
        "content": response["content"],
        "citations": response.get("citations", []),
        "model": model,
        "tokens_used": response["usage"].get("total_tokens", 0),
        "cost_usd": cost,
        "timeframe_days": days,
        "search_after_date": date_filter,
        "metadata": {
            "timeframe_days": days,
            "search_after_date": date_filter,
            "domain_filter": domain_filter,
            "prompt_tokens": response["usage"].get("prompt_tokens", 0),
            "completion_tokens": response["usage"].get("completion_tokens", 0)
        }
    }

    if return_related and "related_questions" in response:
        result["related_questions"] = response["related_questions"]

    return result
