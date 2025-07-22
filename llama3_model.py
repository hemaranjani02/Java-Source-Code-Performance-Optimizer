from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import traceback

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://localhost:11434/api/generate"

# --- Java Optimization Route ---
@app.route("/optimize-java", methods=["POST"])
def optimize_java():
    try:
        data = request.json
        java_code = data.get("code")
        if not java_code:
            return jsonify({"error": "No code provided"}), 400

        print("DEBUG: Received Java code. Preparing prompt...")

        prompt = f"""Performance optimize the following Java code for a Spring Boot microservice:\n\n{java_code}"""
        payload = {
            "model": "llama3:8b",
            "prompt": prompt,
            "stream": False
        }

        print("DEBUG: Sending request to Ollama...")
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        print("DEBUG: Received response from Ollama.")
        return jsonify({"optimized": result.get("response")})

    except requests.exceptions.RequestException as req_err:
        print(f"❌ HTTP Error during Ollama call: {req_err}")
        return jsonify({"error": "Failed to reach Ollama server"}), 500
    except Exception as e:
        print(f"❌ Unexpected error in /optimize-java route: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# --- Run the app ---
if __name__ == "__main__":
    app.run(port=5000, debug=True, use_reloader=False)
