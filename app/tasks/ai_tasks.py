"""AI Analysis Celery Tasks"""

import asyncio
from typing import Dict, Any
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import get_mongodb_client
from app.services.ai_analyzer import AIAnalyzer
from app.schemas.ai_analysis import ConfigRequirements
from app.core.config import settings


def get_ai_analyzer() -> AIAnalyzer:
    """Get AIAnalyzer instance with dependencies"""
    mongo_client = get_mongodb_client()
    return AIAnalyzer(
        mongo_client=mongo_client,
        openai_api_key=settings.OPENAI_API_KEY
    )


@celery_app.task(
    bind=True,
    name="app.tasks.ai_tasks.analyze_feasibility",
    max_retries=3,
    default_retry_delay=60
)
def analyze_feasibility_task(
    self,
    task_id: str,
    config: Dict[str, Any],
    tool_name: str = None
) -> Dict[str, Any]:
    """
    Celery task for AI feasibility analysis.
    
    This task runs asynchronously to analyze MCP tool configurations
    for feasibility. Results are stored in MongoDB with the task_id.
    
    Args:
        task_id: Unique task identifier for result storage
        config: MCP configuration to analyze
        tool_name: Optional tool name for context
    
    Returns:
        Feasibility report as dictionary
    
    Retry Strategy:
        - Max retries: 3
        - Exponential backoff: 60s * (2 ** retry_count)
    
    Validates: Requirements 9.1
    """
    try:
        # Get analyzer instance
        analyzer = get_ai_analyzer()
        
        # Run async analysis in event loop
        loop = asyncio.get_event_loop()
        report = loop.run_until_complete(
            analyzer.analyze_feasibility(config, tool_name)
        )
        
        # Store result in MongoDB
        loop.run_until_complete(
            analyzer.store_analysis_result(
                task_id=UUID(task_id),
                task_type="feasibility_analysis",
                result=report,
                ttl_hours=24
            )
        )
        
        return report.model_dump()
        
    except Exception as exc:
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    bind=True,
    name="app.tasks.ai_tasks.suggest_improvements",
    max_retries=3,
    default_retry_delay=60
)
def suggest_improvements_task(
    self,
    task_id: str,
    tool_name: str,
    description: str,
    config: Dict[str, Any]
) -> list:
    """
    Celery task for generating improvement suggestions.
    
    This task runs asynchronously to analyze MCP tools and generate
    actionable improvement recommendations.
    
    Args:
        task_id: Unique task identifier for result storage
        tool_name: Name of the tool
        description: Tool description
        config: Current tool configuration
    
    Returns:
        List of improvement suggestions as dictionaries
    
    Retry Strategy:
        - Max retries: 3
        - Exponential backoff: 60s * (2 ** retry_count)
    
    Validates: Requirements 9.1
    """
    try:
        # Get analyzer instance
        analyzer = get_ai_analyzer()
        
        # Run async analysis in event loop
        loop = asyncio.get_event_loop()
        improvements = loop.run_until_complete(
            analyzer.suggest_improvements(tool_name, description, config)
        )
        
        # Store result in MongoDB
        loop.run_until_complete(
            analyzer.store_analysis_result(
                task_id=UUID(task_id),
                task_type="improvement_suggestions",
                result=improvements,
                ttl_hours=24
            )
        )
        
        return [imp.model_dump() for imp in improvements]
        
    except Exception as exc:
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    bind=True,
    name="app.tasks.ai_tasks.generate_config",
    max_retries=3,
    default_retry_delay=60
)
def generate_config_task(
    self,
    task_id: str,
    requirements: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Celery task for auto-configuration generation.
    
    This task runs asynchronously to generate MCP configurations
    based on provided requirements.
    
    Args:
        task_id: Unique task identifier for result storage
        requirements: Configuration requirements as dictionary
    
    Returns:
        Generated MCP configuration as dictionary
    
    Retry Strategy:
        - Max retries: 3
        - Exponential backoff: 60s * (2 ** retry_count)
    
    Validates: Requirements 9.1
    """
    try:
        # Get analyzer instance
        analyzer = get_ai_analyzer()
        
        # Parse requirements
        config_requirements = ConfigRequirements(**requirements)
        
        # Run async generation in event loop
        loop = asyncio.get_event_loop()
        config = loop.run_until_complete(
            analyzer.generate_config(config_requirements)
        )
        
        # Store result in MongoDB
        loop.run_until_complete(
            analyzer.store_analysis_result(
                task_id=UUID(task_id),
                task_type="config_generation",
                result=config,
                ttl_hours=24
            )
        )
        
        return config
        
    except Exception as exc:
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
