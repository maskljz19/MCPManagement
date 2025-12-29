"""Celery Tasks Package"""

# Import tasks to register them with Celery
from app.tasks.ai_tasks import (
    analyze_feasibility_task,
    suggest_improvements_task,
    generate_config_task
)
from app.tasks.github_tasks import (
    sync_repository_task
)
from app.tasks.embedding_tasks import (
    generate_embeddings_task
)

__all__ = [
    "analyze_feasibility_task",
    "suggest_improvements_task",
    "generate_config_task",
    "sync_repository_task",
    "generate_embeddings_task"
]
