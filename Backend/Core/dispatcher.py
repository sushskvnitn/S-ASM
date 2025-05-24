from tasks.scanner_tasks import run_full_scan

def run_tasks(target):
    task = run_full_scan.delay(target)
    return {"task_id": task.id}