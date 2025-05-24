from flask import Flask, request, jsonify
from Core.dispatcher import run_tasks

app = Flask(__name__)

@app.route('/start-scan', methods=['POST'])
def start_scan():
    data = request.json
    target = data.get('target')

    if not target:
        return jsonify({"error": "Target required"}), 400

    result = run_tasks(target)
    return jsonify({"message": "Scan started", "result": result})

if __name__ == "__main__":
    app.run(debug=True)
