from celery import Celery

celery = Celery(
    'asm_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_default_queue='scan_tasks',
    worker_concurrency=4,
    task_soft_time_limit=1800,
    task_time_limit=1900,
)