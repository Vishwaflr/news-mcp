#!/usr/bin/env python3
"""
Content Query Builder Service - Build article queries for content generation.

Provides functions to:
- Query articles based on selection criteria (keywords, timeframe, sentiment, impact)
- Estimate LLM generation costs based on token usage
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from sqlmodel import Session, select, or_, and_
from app.models.core import Item
from app.models.analysis import ItemAnalysis


def build_article_query(
    selection_criteria: Dict[str, Any],
    session: Session
) -> List[Item]:
    """
    Build and execute article query based on selection criteria.

    Args:
        selection_criteria: Dict with filtering options:
            - keywords: List[str] - Filter by keywords in title/summary
            - timeframe_hours: int - Filter by publication date
            - min_sentiment_score: float - Filter by sentiment (-1.0 to 1.0)
            - max_sentiment_score: float - Filter by sentiment
            - min_impact_score: float - Filter by impact (0.0 to 1.0)
            - min_urgency_score: float - Filter by urgency (0.0 to 1.0)
            - feed_ids: List[int] - Filter by specific feeds
            - categories: List[str] - Filter by categories
            - max_results: int - Limit results (default: 100)
        session: Database session

    Returns:
        List of Item objects matching criteria (with analysis relationship loaded)
    """
    # Start with base query joining analysis data
    query = select(Item).join(
        ItemAnalysis,
        Item.id == ItemAnalysis.item_id,
        isouter=True  # Left join to include items without analysis
    )

    conditions = []

    # 1. Timeframe filter
    if timeframe_hours := selection_criteria.get('timeframe_hours'):
        cutoff = datetime.utcnow() - timedelta(hours=timeframe_hours)
        conditions.append(Item.published >= cutoff)

    # 2. Keywords filter (case-insensitive search in title OR summary)
    if keywords := selection_criteria.get('keywords'):
        keyword_conditions = []
        for keyword in keywords:
            keyword_conditions.append(Item.title.ilike(f'%{keyword}%'))
            keyword_conditions.append(Item.description.ilike(f'%{keyword}%'))
            keyword_conditions.append(Item.summary.ilike(f'%{keyword}%'))
        conditions.append(or_(*keyword_conditions))

    # 3. Feed filter
    if feed_ids := selection_criteria.get('feed_ids'):
        conditions.append(Item.feed_id.in_(feed_ids))

    # 4. Sentiment filter (requires ItemAnalysis)
    min_sentiment = selection_criteria.get('min_sentiment_score')
    max_sentiment = selection_criteria.get('max_sentiment_score')
    if min_sentiment is not None or max_sentiment is not None:
        # Filter items that have analysis
        conditions.append(ItemAnalysis.id.isnot(None))

        if min_sentiment is not None:
            # sentiment_json->>'overall'->>'score' >= min_sentiment
            conditions.append(
                ItemAnalysis.sentiment_json['overall']['score'].astext.cast(float) >= min_sentiment
            )
        if max_sentiment is not None:
            conditions.append(
                ItemAnalysis.sentiment_json['overall']['score'].astext.cast(float) <= max_sentiment
            )

    # 5. Impact filter (requires ItemAnalysis)
    if min_impact := selection_criteria.get('min_impact_score'):
        conditions.append(ItemAnalysis.id.isnot(None))
        conditions.append(
            ItemAnalysis.impact_json['overall'].astext.cast(float) >= min_impact
        )

    # 6. Urgency filter (requires ItemAnalysis)
    if min_urgency := selection_criteria.get('min_urgency_score'):
        conditions.append(ItemAnalysis.id.isnot(None))
        conditions.append(
            ItemAnalysis.sentiment_json['urgency'].astext.cast(float) >= min_urgency
        )

    # Apply all conditions
    if conditions:
        query = query.where(and_(*conditions))

    # Order by publication date (newest first)
    query = query.order_by(Item.published.desc())

    # Limit results
    max_results = selection_criteria.get('max_results', 100)
    query = query.limit(max_results)

    # Execute and return
    articles = session.exec(query).all()
    return articles


def estimate_generation_cost(
    template: 'SpecialReport',
    article_count: int
) -> float:
    """
    Estimate LLM generation cost based on template and article count.

    Calculation:
    - Input tokens = (system prompt + user prompt + articles summary)
    - Output tokens = (estimated based on max_word_count or 2000 default)
    - Cost = (input_tokens * input_price) + (output_tokens * output_price)

    Pricing (as of 2025-10-03):
    - gpt-4o-mini: $0.15/1M input, $0.60/1M output
    - gpt-4o: $2.50/1M input, $10.00/1M output
    - gpt-4-turbo: $10.00/1M input, $30.00/1M output

    Args:
        template: SpecialReport with llm_model and content_structure
        article_count: Number of articles to include

    Returns:
        Estimated cost in USD (float)
    """
    model = template.llm_model

    # Model pricing (per 1M tokens)
    pricing = {
        'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
        'gpt-4o': {'input': 2.50, 'output': 10.00},
        'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
        'gpt-4': {'input': 30.00, 'output': 60.00},  # Legacy
    }

    if model not in pricing:
        # Default to gpt-4o-mini pricing for unknown models
        model = 'gpt-4o-mini'

    model_pricing = pricing[model]

    # Estimate input tokens
    # System instruction (~500 tokens base)
    system_tokens = 500
    if template.system_instruction:
        system_tokens = len(template.system_instruction.split()) * 1.3  # Words to tokens ratio

    # User prompt template (~200 tokens)
    user_prompt_tokens = len(template.llm_prompt_template.split()) * 1.3

    # Articles (each ~200 tokens: title + summary + metadata)
    articles_tokens = article_count * 200

    # Few-shot examples (if present)
    examples_tokens = 0
    if template.few_shot_examples:
        examples = template.few_shot_examples.get('examples', [])
        for example in examples:
            if isinstance(example, dict):
                examples_tokens += len(str(example.get('output', '')).split()) * 1.3
            elif isinstance(example, str):
                examples_tokens += len(example.split()) * 1.3

    total_input_tokens = system_tokens + user_prompt_tokens + articles_tokens + examples_tokens

    # Estimate output tokens
    # Use max_word_count from output_constraints, or default to 2000 words
    max_words = 2000
    if template.output_constraints:
        max_words = template.output_constraints.get('max_word_count', 2000)

    output_tokens = max_words * 1.3  # Words to tokens

    # Calculate cost
    input_cost = (total_input_tokens / 1_000_000) * model_pricing['input']
    output_cost = (output_tokens / 1_000_000) * model_pricing['output']
    total_cost = input_cost + output_cost

    return round(total_cost, 6)  # Return cost in USD with 6 decimal precision
