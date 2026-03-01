# Entry point for the Celery worker.
# Run with: celery -A celery_worker.celery worker --loglevel=info
from asm_tasks import celery  # noqa: F401 - re-exported for Celery CLI

# Register all tasks by importing the task modules here.
# This must come AFTER the celery app is defined above.
import tasks.scanner_tasks  # noqa: F401