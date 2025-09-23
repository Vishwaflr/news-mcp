"""
Cost Estimation Service for AI Analysis
Provides cost calculations for different AI models and token usage
"""
from app.core.logging_config import get_logger
from typing import Dict, Any, Optional
import os
import math

logger = get_logger(__name__)

class CostEstimatorService:
    """Service for estimating AI analysis costs"""

    # Model pricing per 1K tokens (as of 2024)
    MODEL_PRICING = {
        "gpt-4o-mini": {
            "input": 0.00015,   # $0.15 per 1M tokens
            "output": 0.0006    # $0.60 per 1M tokens
        },
        "gpt-4.1-nano": {
            "input": 0.0001,    # $0.10 per 1M tokens
            "output": 0.0004    # $0.40 per 1M tokens
        },
        "gpt-4": {
            "input": 0.03,      # $30 per 1M tokens
            "output": 0.06      # $60 per 1M tokens
        }
    }

    def __init__(self):
        # Load custom pricing from environment if available
        self._load_custom_pricing()

    def _load_custom_pricing(self):
        """Load custom model pricing from environment variables"""
        try:
            costs_env = os.getenv("ANALYSIS_MODEL_COSTS")
            if costs_env:
                import json
                custom_costs = json.loads(costs_env)
                self.MODEL_PRICING.update(custom_costs)
                logger.info(f"Loaded custom model pricing: {custom_costs}")
        except Exception as e:
            logger.warning(f"Failed to load custom pricing from environment: {e}")

    def estimate_tokens_for_content(self, content: str) -> int:
        """Estimate token count for text content"""
        # Rough approximation: 1 token ≈ 4 characters for English text
        # This is a simplified calculation, real tokenization would be more accurate
        return max(1, len(content) // 4)

    def estimate_article_tokens(self, article_count: int, avg_article_length: int = 1000) -> Dict[str, int]:
        """Estimate token usage for analyzing articles"""

        # Base prompt tokens (system prompt, instructions, etc.)
        base_prompt_tokens = 300

        # Per-article input tokens (title + content + metadata)
        input_tokens_per_article = self.estimate_tokens_for_content("x" * avg_article_length)

        # Expected output tokens per article (sentiment analysis response)
        output_tokens_per_article = 150  # JSON response with sentiment, confidence, etc.

        total_input_tokens = base_prompt_tokens + (article_count * input_tokens_per_article)
        total_output_tokens = article_count * output_tokens_per_article

        return {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens
        }

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Dict[str, Any]:
        """Calculate cost for given model and token usage"""

        if model not in self.MODEL_PRICING:
            return {
                "error": f"Pricing not available for model: {model}",
                "available_models": list(self.MODEL_PRICING.keys())
            }

        pricing = self.MODEL_PRICING[model]

        # Calculate costs (pricing is per 1K tokens)
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost

        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "costs": {
                "input_cost_usd": round(input_cost, 6),
                "output_cost_usd": round(output_cost, 6),
                "total_cost_usd": round(total_cost, 6)
            },
            "cost_breakdown": {
                "input_rate_per_1k": pricing["input"],
                "output_rate_per_1k": pricing["output"]
            }
        }

    def estimate_analysis_cost(self, model: str, article_count: int,
                              avg_article_length: int = 1000) -> Dict[str, Any]:
        """Estimate total cost for analyzing a batch of articles"""

        # Get token estimates
        token_usage = self.estimate_article_tokens(article_count, avg_article_length)

        # Calculate cost
        cost_estimate = self.calculate_cost(
            model=model,
            input_tokens=token_usage["input_tokens"],
            output_tokens=token_usage["output_tokens"]
        )

        if "error" in cost_estimate:
            return cost_estimate

        # Add additional metadata
        cost_estimate.update({
            "article_count": article_count,
            "avg_article_length": avg_article_length,
            "cost_per_article": round(cost_estimate["costs"]["total_cost_usd"] / article_count, 6),
            "efficiency_metrics": {
                "tokens_per_article": token_usage["total_tokens"] // article_count,
                "cost_per_1k_articles": round(cost_estimate["costs"]["total_cost_usd"] * 1000 / article_count, 2)
            }
        })

        return cost_estimate

    def compare_models(self, article_count: int, avg_article_length: int = 1000) -> Dict[str, Any]:
        """Compare costs across all available models"""

        comparisons = {}
        token_usage = self.estimate_article_tokens(article_count, avg_article_length)

        for model in self.MODEL_PRICING.keys():
            cost_estimate = self.calculate_cost(
                model=model,
                input_tokens=token_usage["input_tokens"],
                output_tokens=token_usage["output_tokens"]
            )

            if "error" not in cost_estimate:
                comparisons[model] = {
                    "total_cost_usd": cost_estimate["costs"]["total_cost_usd"],
                    "cost_per_article": round(cost_estimate["costs"]["total_cost_usd"] / article_count, 6),
                    "input_cost_usd": cost_estimate["costs"]["input_cost_usd"],
                    "output_cost_usd": cost_estimate["costs"]["output_cost_usd"]
                }

        # Find cheapest and most expensive
        if comparisons:
            costs = [(model, data["total_cost_usd"]) for model, data in comparisons.items()]
            cheapest = min(costs, key=lambda x: x[1])
            most_expensive = max(costs, key=lambda x: x[1])

            return {
                "article_count": article_count,
                "model_comparisons": comparisons,
                "recommendations": {
                    "cheapest": {"model": cheapest[0], "cost_usd": cheapest[1]},
                    "most_expensive": {"model": most_expensive[0], "cost_usd": most_expensive[1]},
                    "savings_potential": round(most_expensive[1] - cheapest[1], 6)
                },
                "token_usage": token_usage
            }

        return {"error": "No valid model pricing available"}

    def get_budget_recommendations(self, budget_usd: float, model: str,
                                  avg_article_length: int = 1000) -> Dict[str, Any]:
        """Get recommendations for article analysis within budget"""

        if model not in self.MODEL_PRICING:
            return {"error": f"Model {model} not supported"}

        # Estimate cost per article
        sample_cost = self.estimate_analysis_cost(model, 1, avg_article_length)
        if "error" in sample_cost:
            return sample_cost

        cost_per_article = sample_cost["cost_per_article"]

        # Calculate how many articles can be analyzed within budget
        max_articles = int(budget_usd / cost_per_article)
        actual_cost = max_articles * cost_per_article
        remaining_budget = budget_usd - actual_cost

        return {
            "budget_usd": budget_usd,
            "model": model,
            "recommendations": {
                "max_articles": max_articles,
                "actual_cost_usd": round(actual_cost, 6),
                "remaining_budget_usd": round(remaining_budget, 6),
                "cost_per_article": cost_per_article
            },
            "batch_suggestions": {
                "small_batch": min(50, max_articles),
                "medium_batch": min(200, max_articles),
                "large_batch": min(1000, max_articles)
            }
        }

# Global instance
_cost_estimator = None

def get_cost_estimator() -> CostEstimatorService:
    """Get global cost estimator instance"""
    global _cost_estimator
    if _cost_estimator is None:
        _cost_estimator = CostEstimatorService()
    return _cost_estimator