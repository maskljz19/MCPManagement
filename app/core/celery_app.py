"""Celery Application Configuration"""

from celery import Celery
from app.core.config import settings


def make_celery() -> Celery:
    """
    Create and configure Celery application instance.
    
    Returns:
        Configured Celery application
    """
    try:
        # Construct RabbitMQ broker URL
        broker_url = (
            f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}"
            f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}//"
        )

        # Construct Redis result backend URL
        redis_password_part = f":{settings.REDIS_PASSWORD}@" if settings.REDIS_PASSWORD else "@"
        result_backend = (
            f"redis://{redis_password_part}{settings.REDIS_HOST}:"
            f"{settings.REDIS_PORT}/{settings.REDIS_DB}"
        )

        # Create Celery app
        celery_app = Celery(
            "mcp_platform",
            broker=broker_url,
            backend=result_backend,
            include=[
                "app.tasks.ai_tasks",
                "app.tasks.github_tasks",
                "app.tasks.embedding_tasks"
            ]
        )

        # Configure Celery
        celery_app.conf.update(
            # Task execution settings
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,

            # Task result settings
            result_expires=3600,  # Results expire after 1 hour
            result_backend_transport_options={
                "master_name": "mymaster",
                "visibility_timeout": 3600,
            },

            # Beat schedule configuration
            beat_schedule={
                # Example scheduled task - adjust as needed
                'health-check-task': {
                    'task': 'app.tasks.ai_tasks.health_check',
                    'schedule': 60.0,  # Run every 60 seconds
                },
            },

            # Task routing
            task_routes={
                "app.tasks.ai_tasks.*": {"queue": "ai_analysis"},
                "app.tasks.github_tasks.*": {"queue": "github_sync"},
                "app.tasks.embedding_tasks.*": {"queue": "embeddings"},
            },

            # Worker settings
            worker_prefetch_multiplier=4,
            worker_max_tasks_per_child=1000,

            # Task execution limits
            task_time_limit=300,  # 5 minutes hard limit
            task_soft_time_limit=240,  # 4 minutes soft limit

            # Retry settings
            task_acks_late=True,
            task_reject_on_worker_lost=True,

            # Monitoring
            worker_send_task_events=True,
            task_send_sent_event=True,
        )

        return celery_app
    except Exception as e:
        print(f"Celery configuration error: {e}")
        raise


# Create global Celery app instance
celery_app = make_celery()
