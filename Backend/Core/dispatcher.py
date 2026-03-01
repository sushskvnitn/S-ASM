from tasks.scanner_tasks import run_full_scan


def run_tasks(target: str) -> dict:
    """Dispatch a full scan task via Celery and return the task ID."""
    task = run_full_scan.delay(target)
    return {"task_id": task.id}