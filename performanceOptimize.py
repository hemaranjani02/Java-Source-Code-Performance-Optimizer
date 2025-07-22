from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
from sentence_transformers import SentenceTransformer
import chromadb
import traceback
import os

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://localhost:11434/api/generate"
#EXCEL_FILE_PATH = os.path.join("backend", "Book2.xlsx")
EXCEL_FILE_PATH = os.path.join("backend", "Performence_Best_Practices.xlsx")


# Initialize shared components
try:
    print("DEBUG: Initializing SentenceTransformer...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("DEBUG: SentenceTransformer initialized.")

    print("DEBUG: Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path="./chroma_store")
    collection = client.get_or_create_collection("java_feedback")
    print("DEBUG: ChromaDB collection ready.")
except Exception as e:
    print(f"❌ Error during initialization: {e}")
    traceback.print_exc()


# 1. Read Excel and return (observation, recommendation) pairs
def extract_from_excel(excel_path):
    try:
        print(f"DEBUG: Reading Excel file at {excel_path}")
        df = pd.read_excel(excel_path)
        df.columns = df.columns.str.strip()
        print("DEBUG: Excel columns:", df.columns.tolist())

        if "Observation" in df.columns and "Recommendation" in df.columns:
            df = df.dropna(subset=["Observation", "Recommendation"])
            print(f"DEBUG: Extracted {len(df)} rows with Observation and Recommendation")
            print("DEBUG: Sample row:")
            print(df[["Observation", "Recommendation"]].head(1))
            return list(zip(df["Observation"], df["Recommendation"]))
        else:
            print("❌ ERROR: 'Observation' or 'Recommendation' column missing.")
            return []
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        traceback.print_exc()
        return []


# 2. Embed and store in ChromaDB
def store_in_vector_db(pairs):
    try:
        #print(f"DEBUG: Initial collection count: {collection.count()}")
        print("DEBUG: Starting to store pairs in ChromaDB...")

        for i, (obs, rec) in enumerate(pairs):
            try:
                # Ensure both are strings and clean newlines
                obs = str(obs).replace("\n", " ").strip()
                rec = str(rec).replace("\n", " ").strip()

                print(f"  ➤ Encoding and storing pair #{i+1}")
                print(f"    Observation: {obs[:60]}...")
                print(f"    Recommendation: {rec[:60]}...")

                embedding = model.encode(obs)

                collection.add(
                    documents=[obs],
                    metadatas=[{"recommendation": rec}],
                    ids=[f"obs_{i}"],
                    embeddings=[embedding.tolist()]
                )

                print(f"    ✅ Stored obs_{i} successfully.")
            except Exception as inner_e:
                print(f"    ❌ Failed to store pair #{i+1}: {inner_e}")
                traceback.print_exc()

        print(f"DEBUG: Final collection count after insert: {collection.count()}")
    except Exception as e:
        print(f"❌ Error in store_in_vector_db(): {e}")
        traceback.print_exc()




# 3. Search relevant observation by code
def get_relevant_observations(code):
    try:
        print(f"DEBUG: Encoding provided Java code for similarity search...")
        embedding = model.encode(code).tolist()
        results = collection.query(query_embeddings=[embedding], n_results=3)
        print("Retrieved:", results["documents"][0][0])
        print("Recommendation:", results["metadatas"][0][0]["recommendation"])
        print("DEBUG: Top 3 matches:")
        for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
            print(f"\nResult #{i+1}")
            print(f"Observation: {doc}")
            print(f"Recommendation: {meta['recommendation']}")

        return [(doc, meta["recommendation"]) for doc, meta in zip(results["documents"][0], results["metadatas"][0])]
    except Exception as e:
        print(f"❌ Error during ChromaDB query: {e}")
        traceback.print_exc()
        return []


# --- Java Route ---
@app.route("/optimize-java", methods=["POST"])
def optimize_java():
    try:
        data = request.json
        java_code = data.get("code")
        if not java_code:
            return jsonify({"error": "No code provided"}), 400

        context_pairs = get_relevant_observations(java_code)
        context_str = "\n\n".join([f"Observation: {obs}\nRecommendation: {rec}" for obs, rec in context_pairs])
        print(f"DEBUG: Constructed context for LLaMA:\n{context_str}")

        prompt = f"""Based on the following Observations and Recommendations:\n{context_str}\n\nPerformance Optimize this Java code for Spring Boot microservice:\n{java_code}"""
        payload = {"model": "llama3:8b", "prompt": prompt, "stream": False}

        print("DEBUG: Sending prompt to Ollama...")
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



# --- Python Route ---
@app.route("/optimize-python", methods=["POST"])
def optimize_python():
    data = request.json
    python_code = data.get("code")
    if not python_code:
        return jsonify({"error": "No Python code provided"}), 400

    try:
        prompt = f"Performance Optimize the following Python code and explain any improvements:\n\n{python_code}"

        payload = {"model": "llama3:8b", "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        result = response.json()
        return jsonify({"optimized": result.get("response")})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- JavaScript Optimization Route ---
@app.route("/optimize-js", methods=["POST"])
def optimize_js_code():
    data = request.json
    js_code = data.get("code")
    if not js_code:
        return jsonify({"error": "No JavaScript code provided"}), 400

    try:
        prompt = f"Performance optimize the following JavaScript code and explain the improvements:\n\n{js_code}"
        payload = {"model": "llama3:8b", "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        result = response.json()
        return jsonify({"optimized": result.get("response")})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
# --- Summarize Problem Context ---
@app.route("/summarize", methods=["POST"])
def summarize():
    data = request.json
    prompt = (
        f"Summarize the following:\n"
        f"Problem: {data['problem']}\n"
        f"Impact: {data['impact']}\n"
        f"Root Cause: {data['rootCause']}\n"
        f"Fix: {data['fix']}\n\n"
        f"Summarize this issue in 5 lines."
    )

    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        result = response.json()
        return jsonify({"summary": result.get("response", "").strip()})
    except Exception as e:
        return jsonify({"summary": f"Error: {str(e)}"}), 500
    
# --- Decompose Summarized Output ---
@app.route("/decompose-summary", methods=["POST"])
def decompose_summary():
    data = request.json
    summary_text = data.get("summary", "")

    prompt = (
        f"The following is a summarized issue:\n\n"
        f"{summary_text}\n\n"
        f"Extract and return the following in plain text:\n"
        f"Problem Statement:\nImpact of Problem:\nRoot Cause:\nFix of Problem:\n\n"
        f"Format the output exactly like:\n"
        f"Problem: <...>\nImpact: <...>\nRoot Cause: <...>\nFix: <...>"
    )

    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        result = response.json()
        output = result.get("response", "")

        # Simple parsing logic
        lines = output.strip().splitlines()
        parsed = {"problem": "", "impact": "", "rootCause": "", "fix": ""}
        for line in lines:
            if line.lower().startswith("problem:"):
                parsed["problem"] = line.split(":", 1)[-1].strip()
            elif line.lower().startswith("impact:"):
                parsed["impact"] = line.split(":", 1)[-1].strip()
            elif line.lower().startswith("root cause:"):
                parsed["rootCause"] = line.split(":", 1)[-1].strip()
            elif line.lower().startswith("fix:"):
                parsed["fix"] = line.split(":", 1)[-1].strip()

        return jsonify(parsed)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Main ---
if __name__ == "__main__":
    with app.app_context():
        try:
            if os.path.exists(EXCEL_FILE_PATH):
                pairs = extract_from_excel(EXCEL_FILE_PATH)
                print(f"DEBUG: Extracted pairs count: {len(pairs)}")
                for obs, rec in pairs[:3]:
                    print(f"Observation: {obs}\nRecommendation: {rec}\n")
                store_in_vector_db(pairs)
                print(f"DEBUG: Total docs in collection after insert: {collection.count()}")
            else:
                print(f"❌ Excel file not found at: {EXCEL_FILE_PATH}")
        except Exception as e:
            print(f"❌ Error during data load: {e}", flush=True)
            traceback.print_exc()

    # Start the Flask app
    app.run(port=5000, debug=True, use_reloader=False)



