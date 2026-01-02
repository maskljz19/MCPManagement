"""AI Analysis API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from uuid import UUID, uuid4
from typing import Dict, Any, List

from app.core.database import get_mongodb, get_redis
from app.services.ai_analyzer import AIAnalyzer
from app.services.task_tracker import TaskTracker
from app.schemas.ai_analysis import (
    FeasibilityReport,
    Improvement,
    ImprovementRequest,
    ConfigRequirements
)
from app.tasks.ai_tasks import (
    analyze_feasibility_task,
    suggest_improvements_task,
    generate_config_task
)
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis
from app.api.v1.auth import get_current_user
from app.models.user import UserModel
from app.api.dependencies import require_permission


router = APIRouter(prefix="/analyze", tags=["ai-analysis"])


def get_ai_analyzer(
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongodb)
) -> AIAnalyzer:
    """Dependency injection for AIAnalyzer"""
    from app.core.config import settings
    mongo_client = mongo_db.client
    return AIAnalyzer(
        mongo_client=mongo_client,
        openai_api_key=settings.OPENAI_API_KEY
    )


def get_task_tracker(redis: Redis = Depends(get_redis)) -> TaskTracker:
    """Dependency injection for TaskTracker"""
    return TaskTracker(redis=redis)


@router.post("/feasibility", response_model=Dict[str, Any])
@require_permission("analyze", "create")
async def analyze_feasibility(
    config: Dict[str, Any],
    tool_name: str = None,
    async_mode: bool = False,
    analyzer: AIAnalyzer = Depends(get_ai_analyzer),
    tracker: TaskTracker = Depends(get_task_tracker),
    current_user: UserModel = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Analyze feasibility of an MCP tool configuration.
    
    This endpoint evaluates an MCP configuration and returns a feasibility
    assessment including score, reasoning, risks, and recommendations.
    
    Args:
        config: MCP configuration to analyze
        tool_name: Optional tool name for context
        async_mode: If True, process asynchronously and return task_id
    
    Returns:
        If async_mode=False: FeasibilityReport directly
        If async_mode=True: {"task_id": UUID, "status": "pending"}
    
    Raises:
        400: Invalid configuration format
        500: Analysis failed
    
    Validates: Requirements 3.1
    """
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration cannot be empty"
        )
    
    # If async mode, queue task and return task_id
    if async_mode:
        task_id = uuid4()
        
        # Mark task as pending
        await tracker.mark_task_pending(
            task_id=task_id,
            message="Feasibility analysis queued"
        )
        
        # Queue Celery task
        analyze_feasibility_task.apply_async(
            args=[str(task_id), config, tool_name],
            task_id=str(task_id)
        )
        
        return {
            "task_id": str(task_id),
            "status": "pending",
            "message": "Feasibility analysis queued. Use GET /api/v1/tasks/{task_id} to check status."
        }
    
    # Synchronous mode - analyze immediately
    try:
        report = await analyzer.analyze_feasibility(config, tool_name)
        return report.model_dump()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feasibility analysis failed: {str(e)}"
        )


@router.post("/improvements", response_model=Dict[str, Any])
@require_permission("analyze", "create")
async def get_improvements(
    request: ImprovementRequest,
    async_mode: bool = False,
    analyzer: AIAnalyzer = Depends(get_ai_analyzer),
    tracker: TaskTracker = Depends(get_task_tracker),
    current_user: UserModel = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get improvement suggestions for an MCP tool.
    
    This endpoint analyzes an MCP tool and generates actionable
    improvement recommendations across various categories.
    
    Args:
        request: Improvement request containing tool_name, description, and config
        async_mode: If True, process asynchronously and return task_id
    
    Returns:
        If async_mode=False: {"improvements": List[Improvement]}
        If async_mode=True: {"task_id": UUID, "status": "pending"}
    
    Raises:
        400: Invalid input
        500: Analysis failed
    
    Validates: Requirements 3.2
    """
    
    # If async mode, queue task and return task_id
    if async_mode:
        task_id = uuid4()
        
        # Mark task as pending
        await tracker.mark_task_pending(
            task_id=task_id,
            message="Improvement analysis queued"
        )
        
        # Queue Celery task
        suggest_improvements_task.apply_async(
            args=[str(task_id), request.tool_name, request.description, request.config],
            task_id=str(task_id)
        )
        
        return {
            "task_id": str(task_id),
            "status": "pending",
            "message": "Improvement analysis queued. Use GET /api/v1/tasks/{task_id} to check status."
        }
    
    # Synchronous mode - analyze immediately
    try:
        improvements = await analyzer.suggest_improvements(
            tool_name=request.tool_name,
            description=request.description,
            config=request.config
        )
        return {
            "improvements": [imp.model_dump() for imp in improvements]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Improvement analysis failed: {str(e)}"
        )


@router.post("/generate-config", response_model=Dict[str, Any])
@require_permission("analyze", "create")
async def generate_configuration(
    requirements: ConfigRequirements,
    async_mode: bool = False,
    analyzer: AIAnalyzer = Depends(get_ai_analyzer),
    tracker: TaskTracker = Depends(get_task_tracker),
    current_user: UserModel = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate an MCP configuration based on requirements.
    
    This endpoint uses AI to automatically generate a valid MCP
    configuration from high-level requirements.
    
    Args:
        requirements: Configuration requirements (tool name, description, capabilities, constraints)
        async_mode: If True, process asynchronously and return task_id
    
    Returns:
        If async_mode=False: {"config": Dict[str, Any]}
        If async_mode=True: {"task_id": UUID, "status": "pending"}
    
    Raises:
        400: Invalid requirements
        500: Generation failed
    
    Validates: Requirements 3.3
    """
    # If async mode, queue task and return task_id
    if async_mode:
        task_id = uuid4()
        
        # Mark task as pending
        await tracker.mark_task_pending(
            task_id=task_id,
            message="Configuration generation queued"
        )
        
        # Queue Celery task
        generate_config_task.apply_async(
            args=[str(task_id), requirements.model_dump()],
            task_id=str(task_id)
        )
        
        return {
            "task_id": str(task_id),
            "status": "pending",
            "message": "Configuration generation queued. Use GET /api/v1/tasks/{task_id} to check status."
        }
    
    # Synchronous mode - generate immediately
    try:
        config = await analyzer.generate_config(requirements)
        return {"config": config}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration generation failed: {str(e)}"
        )
