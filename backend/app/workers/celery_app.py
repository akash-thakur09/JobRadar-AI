"""Celery application factory and configuration."""

from celery import Celery
from kombu.entity import Exchange, Queue

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "jobradar_workers",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks",
        "app.modules.resumes.tasks",
        "app.modules.discovery.tasks",
        "app.modules.jobs.tasks",
        "app.modules.matching.tasks",
    ],
)

# Define explicit task queues matching technical design TD-007
default_exchange = Exchange("default", type="direct")
celery_app.conf.task_queues = (
    Queue("discovery", default_exchange, routing_key="discovery"),
    Queue("processing", default_exchange, routing_key="processing"),
    Queue("tailoring", default_exchange, routing_key="tailoring"),
    Queue("notifications", default_exchange, routing_key="notifications"),
)

celery_app.conf.update(
    task_default_queue="processing",
    task_default_exchange="default",
    task_default_routing_key="processing",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "schedule-due-discovery-runs": {
            "task": "app.modules.jobs.tasks.schedule_due_discovery_runs_task",
            "schedule": 300.0,  # every 5 minutes
        },
        "process-pending-raw-jobs": {
            "task": "app.modules.jobs.tasks.process_pending_raw_records_task",
            "schedule": 120.0,  # every 2 minutes
        },
    },
)
