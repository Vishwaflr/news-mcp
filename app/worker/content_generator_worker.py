#!/usr/bin/env python3
"""
Content Generator Worker - Processes pending content generation jobs.

Similar to analysis_worker.py but for content distribution system.
Polls pending_content_generation table and generates content using LLM.
"""

import os
import sys

# Add project root to Python path FIRST
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import time
import signal
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.logging_config import get_logger, setup_logging
from app.database import get_session
from contextlib import contextmanager

@contextmanager
def get_session_context():
    """Context manager for database sessions."""
    session = next(get_session())
    try:
        yield session
    finally:
        session.close()
from app.models.content_distribution import (
    PendingContentGeneration,
    ContentTemplate,
    GeneratedContent
)
from app.models.core import Item
from app.models.analysis import ItemAnalysis
from app.services.content_query_builder import build_article_query, estimate_generation_cost
from sqlmodel import select
import openai

# Configure structured logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)


class ContentGeneratorWorker:
    """
    Content Generator Worker - Processes content generation queue.

    Workflow:
    1. Poll pending_content_generation table for pending jobs
    2. For each job:
       a. Load template configuration
       b. Query matching articles
       c. Prepare LLM context
       d. Call OpenAI API with template prompt
       e. Parse and validate response
       f. Store generated content
       g. Mark job as complete
    """

    def __init__(self):
        self.running = True
        self.worker_id = f"content-worker-{os.getpid()}"
        self.openai_client = None

        self._setup_signal_handlers()
        self._load_config()
        self._init_openai()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.running = False

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _load_config(self):
        """Load configuration from environment variables."""
        self.config = {
            'sleep_interval': float(os.getenv('CONTENT_WORKER_SLEEP_INTERVAL', '5.0')),
            'max_jobs_per_cycle': int(os.getenv('CONTENT_WORKER_MAX_JOBS', '5')),
            'job_timeout_seconds': int(os.getenv('CONTENT_WORKER_JOB_TIMEOUT', '300')),
            'max_cost_per_job': float(os.getenv('CONTENT_MAX_COST_PER_JOB', '0.50')),
        }
        logger.info(f"Content Worker config loaded: {self.config}")

    def _init_openai(self):
        """Initialize OpenAI client."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY not set!")
            raise ValueError("OPENAI_API_KEY environment variable required")

        self.openai_client = openai.OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized")

    def start(self):
        """Start the worker main loop."""
        logger.info(f"Starting Content Generator Worker (ID: {self.worker_id})")

        try:
            while self.running:
                try:
                    self._process_queue()
                except Exception as e:
                    logger.error(f"Error in worker cycle: {e}", exc_info=True)

                if self.running:
                    time.sleep(self.config['sleep_interval'])

        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
        finally:
            logger.info("Content Generator Worker stopped")

    def _process_queue(self):
        """Process pending content generation jobs."""
        with get_session_context() as session:
            # Get pending jobs
            pending_jobs = session.exec(
                select(PendingContentGeneration)
                .where(PendingContentGeneration.status == 'pending')
                .limit(self.config['max_jobs_per_cycle'])
            ).all()

            if not pending_jobs:
                logger.debug("No pending content generation jobs")
                return

            logger.info(f"Found {len(pending_jobs)} pending content generation job(s)")

            for job in pending_jobs:
                if not self.running:
                    break

                try:
                    self._process_job(job, session)
                except Exception as e:
                    logger.error(f"Error processing job {job.id}: {e}", exc_info=True)
                    self._mark_job_failed(job, str(e), session)

    def _process_job(self, job: PendingContentGeneration, session):
        """Process a single content generation job."""
        logger.info(f"Processing content generation job {job.id} for template {job.template_id}")

        # Mark as processing
        job.status = 'processing'
        job.started_at = datetime.utcnow()
        job.worker_id = self.worker_id
        session.add(job)
        session.commit()

        # Load template
        template = session.get(ContentTemplate, job.template_id)
        if not template:
            raise ValueError(f"Template {job.template_id} not found")

        if not template.is_active:
            raise ValueError(f"Template {job.template_id} is inactive")

        # Query articles
        articles = build_article_query(template.selection_criteria, session)

        if not articles:
            logger.warning(f"No articles matched template {template.id} criteria")
            raise ValueError("No articles matched selection criteria")

        logger.info(f"Found {len(articles)} articles for template {template.id}")

        # Estimate cost
        estimated_cost = estimate_generation_cost(template, len(articles))
        if estimated_cost > self.config['max_cost_per_job']:
            raise ValueError(
                f"Estimated cost ${estimated_cost:.4f} exceeds max ${self.config['max_cost_per_job']}"
            )

        # Prepare LLM context
        context = self._prepare_llm_context(articles, template)

        # Generate content
        start_time = time.time()
        llm_response = self._call_llm(template, context)
        generation_time = int(time.time() - start_time)

        # Parse response
        content_data = self._parse_llm_response(llm_response, template)

        # Store generated content
        generated_content = GeneratedContent(
            template_id=template.id,
            title=content_data.get('title') or f"{template.name} - {datetime.utcnow().strftime('%Y-%m-%d')}",
            content_html=content_data.get('html'),
            content_markdown=content_data.get('markdown'),
            content_json=content_data.get('json'),
            source_article_ids=[a.id for a in articles],
            articles_count=len(articles),
            generation_job_id=str(job.id),
            word_count=content_data.get('word_count'),
            generation_cost_usd=Decimal(str(estimated_cost)),
            generation_time_seconds=generation_time,
            llm_model_used=template.llm_model,
            status='generated'
        )

        session.add(generated_content)
        session.commit()
        session.refresh(generated_content)

        logger.info(
            f"Generated content {generated_content.id} for template {template.id} "
            f"(cost: ${estimated_cost:.4f}, time: {generation_time}s)"
        )

        # Mark job as complete
        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        job.generated_content_id = generated_content.id
        session.add(job)
        session.commit()

        logger.info(f"Job {job.id} completed successfully")

    def _prepare_llm_context(
        self,
        articles: List[Item],
        template: ContentTemplate
    ) -> Dict[str, Any]:
        """
        Prepare context data for LLM prompt.

        Args:
            articles: List of articles to include
            template: Content template

        Returns:
            Context dict with formatted article data
        """
        articles_formatted = []

        for article in articles:
            article_dict = {
                'title': article.title,
                'link': article.link,
                'published': article.published.isoformat() if article.published else None,
                'summary': article.description or article.summary,
            }

            # Add analysis data if available (from JSON fields)
            if hasattr(article, 'item_analysis') and article.item_analysis:
                analysis = article.item_analysis
                # Extract from JSONB fields
                sentiment_data = analysis.sentiment_json.get('overall', {}) if analysis.sentiment_json else {}
                impact_data = analysis.impact_json if analysis.impact_json else {}

                article_dict.update({
                    'sentiment_score': sentiment_data.get('score'),
                    'sentiment_label': sentiment_data.get('label'),
                    'impact_score': impact_data.get('overall'),
                    'urgency_score': analysis.sentiment_json.get('urgency') if analysis.sentiment_json else None,
                })

            articles_formatted.append(article_dict)

        # Get selection criteria summary
        criteria = template.selection_criteria
        criteria_summary = []
        if criteria.get('keywords'):
            criteria_summary.append(f"Keywords: {', '.join(criteria['keywords'])}")
        if criteria.get('timeframe_hours'):
            criteria_summary.append(f"Last {criteria['timeframe_hours']} hours")
        if criteria.get('min_impact_score'):
            criteria_summary.append(f"Min impact: {criteria['min_impact_score']}")

        return {
            'template_name': template.name,
            'target_audience': template.target_audience or 'General',
            'article_count': len(articles),
            'timeframe': criteria.get('timeframe_hours', 'N/A'),
            'criteria_summary': ' | '.join(criteria_summary),
            'articles': articles_formatted,
            'sections': template.content_structure.get('sections', [])
        }

    def _call_llm(
        self,
        template: ContentTemplate,
        context: Dict[str, Any]
    ) -> str:
        """
        Call OpenAI API to generate content using structured prompt.

        Args:
            template: Content template with prompt
            context: Prepared context data

        Returns:
            LLM response text
        """
        # Build system instruction (use new field or fallback to default)
        system_instruction = template.system_instruction or f"""You are a professional content analyst creating structured briefings.
Target Audience: {context['target_audience']}
Output Format: {template.output_format}

Generate content following this exact structure:
"""

        # Add section structure if not using custom system_instruction
        if not template.system_instruction:
            for section in context['sections']:
                system_instruction += f"\n- {section['name']}: {section['prompt']}"
                if section.get('max_words'):
                    system_instruction += f" (max {section['max_words']} words)"
                if section.get('max_items'):
                    system_instruction += f" (max {section['max_items']} items)"

        # Add output constraints if defined
        if template.output_constraints:
            constraints = template.output_constraints

            system_instruction += "\n\nCONSTRAINTS:"

            if constraints.get('forbidden'):
                forbidden_items = ', '.join(constraints['forbidden'])
                system_instruction += f"\n- FORBIDDEN: Do NOT include {forbidden_items}"

            if constraints.get('required'):
                required_items = ', '.join(constraints['required'])
                system_instruction += f"\n- REQUIRED: You MUST include {required_items}"

            if constraints.get('max_word_count'):
                system_instruction += f"\n- MAX LENGTH: {constraints['max_word_count']} words"

            if constraints.get('min_word_count'):
                system_instruction += f"\n- MIN LENGTH: {constraints['min_word_count']} words"

        # Add few-shot examples if provided
        few_shot_messages = []
        if template.few_shot_examples and isinstance(template.few_shot_examples, dict):
            examples = template.few_shot_examples.get('examples', [])
            if examples:
                system_instruction += "\n\nEXAMPLES OF GOOD OUTPUT:\n"
                for idx, example in enumerate(examples[:3], 1):  # Max 3 examples
                    if isinstance(example, dict):
                        system_instruction += f"\n--- Example {idx} ---\n{example.get('output', '')}\n"
                    elif isinstance(example, str):
                        system_instruction += f"\n--- Example {idx} ---\n{example}\n"

        # Build user prompt with articles
        articles_text = "\n\n".join([
            f"[{i+1}] {a['title']}\n"
            f"Source: {a['link']}\n"
            f"Published: {a['published']}\n"
            f"Summary: {a['summary']}\n"
            f"Sentiment: {a.get('sentiment_label', 'N/A')} ({a.get('sentiment_score', 'N/A')})\n"
            f"Impact: {a.get('impact_score', 'N/A')}"
            for i, a in enumerate(context['articles'])
        ])

        user_prompt = template.llm_prompt_template.format(
            **context,
            articles_list=articles_text
        )

        # Add validation reminder if validation_rules exist
        if template.validation_rules:
            validation_reminder = "\n\nVALIDATION CHECKLIST (review your output before submitting):\n"

            if template.validation_rules.get('require_sources'):
                validation_reminder += "- Did you cite all sources?\n"
            if template.validation_rules.get('min_word_count'):
                validation_reminder += f"- Is the output at least {template.validation_rules['min_word_count']} words?\n"
            if template.validation_rules.get('check_for_code'):
                validation_reminder += "- Did you avoid including code blocks?\n"

            user_prompt += validation_reminder

        # Call OpenAI
        logger.info(f"Calling OpenAI API (model: {template.llm_model})")

        response = self.openai_client.chat.completions.create(
            model=template.llm_model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=float(template.llm_temperature),
            max_tokens=4000
        )

        llm_output = response.choices[0].message.content
        logger.debug(f"LLM response received ({len(llm_output)} chars)")

        return llm_output

    def _parse_llm_response(
        self,
        llm_response: str,
        template: ContentTemplate
    ) -> Dict[str, Any]:
        """
        Parse LLM response into structured content.

        Args:
            llm_response: Raw LLM output
            template: Content template

        Returns:
            Dict with parsed content in multiple formats
        """
        output_format = template.content_structure.get('output_format', 'markdown')

        content_data = {
            'word_count': len(llm_response.split()),
        }

        if output_format == 'markdown':
            content_data['markdown'] = llm_response
            # Simple markdown to HTML conversion (basic)
            content_data['html'] = self._markdown_to_html(llm_response)
        elif output_format == 'html':
            content_data['html'] = llm_response
            content_data['markdown'] = llm_response  # Store as-is
        elif output_format == 'json':
            # TODO: Parse JSON response
            content_data['json'] = {'raw': llm_response}
            content_data['markdown'] = llm_response

        return content_data

    def _markdown_to_html(self, markdown: str) -> str:
        """
        Basic markdown to HTML conversion.

        TODO: Use proper markdown library (markdown or mistune)
        """
        html = markdown

        # Headers
        html = html.replace('# ', '<h1>').replace('\n', '</h1>\n', 1)
        html = html.replace('## ', '<h2>').replace('\n', '</h2>\n', 1)
        html = html.replace('### ', '<h3>').replace('\n', '</h3>\n', 1)

        # Paragraphs
        lines = html.split('\n\n')
        html = '\n'.join(f'<p>{line}</p>' if not line.startswith('<h') else line for line in lines)

        return html

    def _mark_job_failed(
        self,
        job: PendingContentGeneration,
        error_message: str,
        session
    ):
        """Mark job as failed with error message."""
        job.status = 'failed'
        job.error_message = error_message
        job.retry_count += 1
        job.completed_at = datetime.utcnow()

        session.add(job)
        session.commit()

        logger.error(f"Job {job.id} marked as failed: {error_message}")


def main():
    """Main entry point."""
    worker = ContentGeneratorWorker()
    worker.start()


if __name__ == "__main__":
    main()
