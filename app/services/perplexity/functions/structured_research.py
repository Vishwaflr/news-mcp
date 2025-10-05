"""
Structured Research Function
Returns research results in structured JSON format
Priority: Very Important - enables automated processing
"""
from typing import Dict, Any
from app.services.perplexity.perplexity_client import PerplexityClient


async def execute(
    query: str,
    parameters: Dict[str, Any],
    client: PerplexityClient
) -> Dict[str, Any]:
    """
    Execute research with structured JSON output

    Parameters:
        query: Research question
        parameters: {
            "json_schema": {  # Required: Output schema definition
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "key_points": {"type": "array", "items": {"type": "string"}},
                    "sources": {"type": "array"}
                }
            },
            "model": "llama-3.1-sonar-small-128k-online"  # Optional
        }

    Returns:
        {
            "structured_data": {...},  # Matches json_schema
            "tokens_used": 1500,
            "cost_usd": 0.0003
        }
    """
    json_schema = parameters.get("json_schema")
    model = parameters.get("model", "llama-3.1-sonar-small-128k-online")

    if not json_schema:
        raise ValueError("json_schema is required for structured research")

    response_format = {
        "type": "json_schema",
        "json_schema": json_schema
    }

    response = await client.structured_search(
        query=query,
        response_format=response_format,
        model=model
    )

    usage = response.get("usage", {})
    cost = client.calculate_cost(usage, model)

    # Parse structured content
    content = response["choices"][0]["message"]["content"]
    import json
    structured_data = json.loads(content)

    return {
        "structured_data": structured_data,
        "model": model,
        "tokens_used": usage.get("total_tokens", 0),
        "cost_usd": cost,
        "metadata": {
            "schema_used": json_schema,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0)
        }
    }
