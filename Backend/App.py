from flask import Flask, request, jsonify
from Core.dispatcher import run_tasks
from Core.environmentsetup import setup_environment

app = Flask(__name__)


@app.route('/')
def index():
    return jsonify({"message": "S-ASM EASM Scanner API", "version": "2.0"}), 200


@app.route('/setup', methods=['POST'])
def setup():
    try:
        result = setup_environment()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/start-scan', methods=['POST'])
def start_scan():
    data = request.json or {}
    target = data.get('target', '').strip()
    if not target:
        return jsonify({"error": "target is required"}), 400
    try:
        result = run_tasks(target)
        return jsonify({"message": "Scan started", "task_id": result["task_id"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/task-status/<task_id>', methods=['GET'])
def task_status(task_id):
    """Check the status and result of a running or completed scan."""
    try:
        from celery.result import AsyncResult
        from asm_tasks import celery
        result = AsyncResult(task_id, app=celery)
        response = {
            "task_id": task_id,
            "status": result.status,   # PENDING / STARTED / SUCCESS / FAILURE
        }
        if result.status == "SUCCESS":
            response["result"] = result.result
        elif result.status == "FAILURE":
            response["error"] = str(result.result)
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/results/<target>', methods=['GET'])
def get_results(target):
    """Return all saved scan results for a target."""
    import os
    import json
    safe = target.replace("://", "_").replace("/", "_").replace(":", "_")
    base = f"storage/results/{safe}"
    if not os.path.isdir(base):
        return jsonify({"error": "No results found for this target"}), 404
    results = {}
    for fname in os.listdir(base):
        if fname.endswith(".json"):
            with open(os.path.join(base, fname)) as f:
                try:
                    results[fname.replace(".json", "")] = json.load(f)
                except Exception:
                    pass
    return jsonify({"target": target, "results": results}), 200


@app.route('/dorking', methods=['POST'])
def dorking():
    data = request.json or {}
    target = data.get('target', '').strip()
    if not target:
        return jsonify({"error": "target is required"}), 400
    try:
        from Modules.dorking import run_dorking_module
        results = run_dorking_module(target)
        return jsonify({"message": "Dorking completed", "results": results}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)