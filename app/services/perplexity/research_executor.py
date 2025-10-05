"""
Research Executor
Executes research templates by loading and running Perplexity functions
"""
import os
import importlib.util
from typing import Dict, Any, Optional
from datetime import datetime
from app.services.perplexity.perplexity_client import PerplexityClient
from app.repositories.research_template_repo import ResearchTemplateRepo
from app.repositories.research_run_repo import ResearchRunRepo
from app.models.research import ResearchRun
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ResearchExecutor:
    """Executes research templates"""

    def __init__(self):
        self.client = PerplexityClient()
        self.functions_dir = os.path.join(
            os.path.dirname(__file__),
            "functions"
        )

    def load_function(self, function_name: str):
        """
        Dynamically load a Perplexity function module

        Args:
            function_name: Name of the function (without .py extension)

        Returns:
            The execute() function from the module
        """
        module_path = os.path.join(self.functions_dir, f"{function_name}.py")

        if not os.path.exists(module_path):
            raise ValueError(f"Function not found: {function_name}")

        try:
            spec = importlib.util.spec_from_file_location(function_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "execute"):
                raise ValueError(f"Function {function_name} does not have an execute() method")

            return module.execute

        except Exception as e:
            logger.error(f"Error loading function {function_name}: {e}")
            raise

    async def execute_template(
        self,
        template_id: int,
        query: Optional[str] = None,
        trigger_type: str = "manual",
        triggered_by: Optional[str] = None
    ) -> ResearchRun:
        """
        Execute a research template

        Args:
            template_id: ID of the template to execute
            query: Optional query override (uses template prompt if None)
            trigger_type: Type of trigger ("manual", "scheduled", "api")
            triggered_by: User/system that triggered the run

        Returns:
            ResearchRun with results
        """
        # Load template
        template = ResearchTemplateRepo.get_by_id(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        if not template.is_active:
            raise ValueError(f"Template is inactive: {template.name}")

        # Use provided query or template llm_prompt as fallback
        actual_query = query or template.llm_prompt

        # Create run record
        run = ResearchRun(
            template_id=template_id,
            status="pending",
            trigger_type=trigger_type,
            query_text=actual_query,
            triggered_by=triggered_by
        )
        run = ResearchRunRepo.create(run)

        try:
            # Update status to running
            ResearchRunRepo.update_status(run.id, "running")

            # Load and execute Perplexity function
            function = self.load_function(template.perplexity_function)

            logger.info(f"Executing research function: {template.perplexity_function} with query: {actual_query[:50]}...")

            perplexity_result = await function(
                query=actual_query,
                parameters=template.function_parameters,
                client=self.client
            )

            # Process result with LLM if needed
            final_content = perplexity_result.get("content", "")
            result_metadata = perplexity_result

            # Calculate costs
            perplexity_cost = perplexity_result.get("cost_usd", 0)
            tokens_used = perplexity_result.get("tokens_used", 0)

            # TODO: Add LLM post-processing if template has llm_prompt different from query
            llm_cost = 0.0  # Placeholder for LLM processing cost

            total_cost = perplexity_cost + llm_cost

            # Update run with results
            ResearchRunRepo.update_results(
                run_id=run.id,
                result_content=final_content,
                result_metadata=result_metadata,
                tokens_used=tokens_used,
                cost_usd=total_cost,
                perplexity_cost_usd=perplexity_cost,
                llm_cost_usd=llm_cost
            )

            # Mark as completed
            ResearchRunRepo.update_status(run.id, "completed")

            logger.info(
                f"Research run {run.id} completed successfully "
                f"(tokens: {tokens_used}, cost: ${total_cost:.6f})"
            )

            # Reload to get updated data
            return ResearchRunRepo.get_by_id(run.id)

        except Exception as e:
            logger.error(f"Research run {run.id} failed: {e}")
            ResearchRunRepo.update_status(run.id, "failed", error_message=str(e))
            raise

    async def execute_run(self, run_id: int) -> ResearchRun:
        """
        Execute an existing pending run

        Args:
            run_id: ID of the run to execute

        Returns:
            Updated ResearchRun
        """
        run = ResearchRunRepo.get_by_id(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        if run.status != "pending":
            raise ValueError(f"Run is not in pending status: {run.status}")

        template = ResearchTemplateRepo.get_by_id(run.template_id)
        if not template:
            raise ValueError(f"Template not found: {run.template_id}")

        try:
            # Update status to running
            ResearchRunRepo.update_status(run.id, "running")

            # Load and execute function
            function = self.load_function(template.perplexity_function)

            perplexity_result = await function(
                query=run.query_text,
                parameters=template.function_parameters,
                client=self.client
            )

            # Extract results
            final_content = perplexity_result.get("content", "")
            perplexity_cost = perplexity_result.get("cost_usd", 0)
            tokens_used = perplexity_result.get("tokens_used", 0)

            # Update run with results
            ResearchRunRepo.update_results(
                run_id=run.id,
                result_content=final_content,
                result_metadata=perplexity_result,
                tokens_used=tokens_used,
                cost_usd=perplexity_cost,
                perplexity_cost_usd=perplexity_cost,
                llm_cost_usd=0.0
            )

            # Mark as completed
            ResearchRunRepo.update_status(run.id, "completed")

            return ResearchRunRepo.get_by_id(run.id)

        except Exception as e:
            logger.error(f"Run {run_id} execution failed: {e}")
            ResearchRunRepo.update_status(run.id, "failed", error_message=str(e))
            raise

    def list_available_functions(self) -> list[str]:
        """List all available Perplexity functions"""
        functions = []
        for filename in os.listdir(self.functions_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                function_name = filename[:-3]  # Remove .py
                functions.append(function_name)
        return sorted(functions)
