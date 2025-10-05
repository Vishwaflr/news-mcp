"""
Multi-Step Pipeline Research Function
Executes research in multiple sequential steps (aspects → deep dive → synthesis)
Priority: Important - for complex analysis workflows
"""
from typing import Dict, Any, List
from app.services.perplexity.perplexity_client import PerplexityClient


# Schema definition for dynamic form generation
SCHEMA = {
    "name": "pipeline_research",
    "display_name": "Pipeline Research",
    "description": "Multi-step research pipeline with sequential analysis phases",
    "icon": "bi-diagram-3",
    "parameters": [
        {
            "name": "steps",
            "display_name": "Pipeline Steps (JSON)",
            "type": "json",
            "required": True,
            "description": "Define the research pipeline steps",
            "placeholder": '''[
  {
    "name": "aspect_discovery",
    "prompt_template": "What are the key aspects of {query}?",
    "extract_keywords": true
  },
  {
    "name": "deep_analysis",
    "prompt_template": "Analyze {aspect} in detail",
    "depends_on": "aspect_discovery"
  },
  {
    "name": "synthesis",
    "prompt_template": "Synthesize findings: {results}",
    "combine_previous": true
  }
]''',
            "help_text": "Each step runs sequentially, using results from previous steps",
            "validation": {
                "type": "json"
            }
        },
        {
            "name": "max_depth",
            "display_name": "Maximum Pipeline Depth",
            "type": "number",
            "default": 3,
            "required": False,
            "description": "Maximum number of steps allowed",
            "validation": {
                "min": 1,
                "max": 10
            }
        }
    ]
}


async def execute(
    query: str,
    parameters: Dict[str, Any],
    client: PerplexityClient
) -> Dict[str, Any]:
    """
    Execute multi-step research pipeline

    Parameters:
        query: Main research topic
        parameters: {
            "steps": [  # Required: Pipeline steps
                {
                    "name": "aspect_discovery",
                    "prompt_template": "What are the key aspects of {query}?",
                    "extract_keywords": true
                },
                {
                    "name": "deep_analysis",
                    "prompt_template": "Analyze {aspect} in detail",
                    "depends_on": "aspect_discovery"
                },
                {
                    "name": "synthesis",
                    "prompt_template": "Synthesize findings: {results}",
                    "combine_previous": true
                }
            ],
            "max_depth": 3,  # Optional: Maximum pipeline depth
            "model": "llama-3.1-sonar-small-128k-online"  # Optional
        }

    Returns:
        {
            "pipeline_results": [
                {"step": "aspect_discovery", "content": "...", "tokens": 500},
                {"step": "deep_analysis", "content": "...", "tokens": 1000},
                {"step": "synthesis", "content": "...", "tokens": 800}
            ],
            "final_result": "...",  # Output of last step
            "total_tokens_used": 2300,
            "total_cost_usd": 0.00046
        }
    """
    steps = parameters.get("steps", [])
    max_depth = parameters.get("max_depth", 3)
    model = parameters.get("model", "sonar")

    if not steps:
        raise ValueError("steps is required for pipeline research")

    if len(steps) > max_depth:
        raise ValueError(f"Pipeline depth exceeds maximum: {len(steps)} > {max_depth}")

    pipeline_results = []
    total_tokens = 0
    total_cost = 0.0
    context = {"query": query}

    for step in steps:
        step_name = step.get("name", "unnamed_step")
        prompt_template = step.get("prompt_template", "{query}")

        # Build prompt from template and context
        prompt = prompt_template.format(**context)

        # Execute step
        response = await client.search(
            query=prompt,
            model=model
        )

        step_tokens = response["usage"].get("total_tokens", 0)
        step_cost = client.calculate_cost(response["usage"], model)

        step_result = {
            "step": step_name,
            "content": response["content"],
            "citations": response.get("citations", []),
            "tokens": step_tokens,
            "cost_usd": step_cost
        }

        pipeline_results.append(step_result)
        total_tokens += step_tokens
        total_cost += step_cost

        # Update context for next step
        if step.get("extract_keywords"):
            # Simple keyword extraction (could be enhanced with NLP)
            keywords = [word.strip() for word in response["content"].split()[:10]]
            context["keywords"] = keywords

        if step.get("combine_previous"):
            # Combine all previous results
            context["results"] = " | ".join([r["content"] for r in pipeline_results[:-1]])

        # Add step result to context
        context[step_name] = response["content"]

    final_result = pipeline_results[-1]["content"] if pipeline_results else ""

    return {
        "pipeline_results": pipeline_results,
        "final_result": final_result,
        "total_tokens_used": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "metadata": {
            "model": model,
            "steps_executed": len(pipeline_results),
            "max_depth": max_depth
        }
    }
