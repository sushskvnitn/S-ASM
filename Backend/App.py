from flask import Flask, request, jsonify
from Core.dispatcher import run_tasks
from Core.environmentsetup import setup_environment

app = Flask(__name__)


@app.route('/')
def index():
    return jsonify({"message": "Welcome to the Vulnerability Scanner API"}), 200


@app.route('/setup', methods=['POST'])
def setup():
    try:
        setup_environment()
        return jsonify({"message": "Environment setup completed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/dorking', methods=['POST'])
def dorking():
    data = request.json
    target = data.get('target')

    if not target:
        return jsonify({"error": "Target required"}), 400

    try:
        # Fix: use the correct function name from dorking module
        from Modules.dorking import run_dorking_module
        results = run_dorking_module(target)
        return jsonify({"message": "Dorking completed", "results": results}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/start-scan', methods=['POST'])
def start_scan():
    data = request.json
    target = data.get('target')

    if not target:
        return jsonify({"error": "Target required"}), 400

    try:
        result = run_tasks(target)
        return jsonify({"message": "Scan started", "result": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)