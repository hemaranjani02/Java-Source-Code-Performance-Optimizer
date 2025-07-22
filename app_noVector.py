from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Allow frontend to access backend

OLLAMA_URL = "http://localhost:11434/api/generate"

@app.route("/optimize", methods=["POST"])
def optimize_code():
    data = request.json
    java_code = data.get("code")

    if not java_code:
        return jsonify({"error": "No code provided"}), 400

    prompt = f"Performance Optimize the following Java code and explain any improvements:\n\n{java_code}"

    payload = {
        "model": "llama3:8b",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        result = response.json()
        print(result)
        return jsonify({"optimized": result.get("response")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)