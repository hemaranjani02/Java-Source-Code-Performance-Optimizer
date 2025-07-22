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
EXCEL_FILE_PATH = os.path.join("backend", "FinalDataset.xlsx")


# Initialize shared components
model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_store")
collection = client.get_or_create_collection("java_feedback")

# 1. Read Excel (all sheets) and return (observation, recommendation) pairs
def extract_from_excel(excel_path):
    all_sheets = pd.read_excel(excel_path, sheet_name=None)
    pairs = []
    for sheet_name, df in all_sheets.items():
        if "Observation" in df.columns and "Recommendation" in df.columns:
            df = df.dropna(subset=["Observation", "Recommendation"])
            for _, row in df.iterrows():
                pairs.append((row["Observation"], row["Recommendation"]))
    return pairs

# 2. Embed and store in ChromaDB
def store_in_vector_db(pairs):
    for i, (obs, rec) in enumerate(pairs):
        embedding = model.encode(obs)
        collection.add(
            documents=[obs],
            metadatas=[{"recommendation": rec}],
            ids=[f"obs_{i}"],
            embeddings=[embedding.tolist()]
        )

# 3. Search relevant observation by code
def get_relevant_observations(code):
    embedding = model.encode(code).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=3)
    return [(doc, meta["recommendation"]) for doc, meta in zip(results["documents"][0], results["metadatas"][0])]

# --- Java Route ---
@app.route("/optimize-java", methods=["POST"])
def optimize_java():
    data = request.json
    java_code = data.get("code")
    if not java_code:
        return jsonify({"error": "No code provided"}), 400

    try:
        context_pairs = get_relevant_observations(java_code)
        context_str = "\n\n".join([f"Observation: {obs}\nRecommendation: {rec}" for obs, rec in context_pairs])

        prompt = f"""Based on the following Observations and Recommendations:\n{context_str}\n\nPerformance Optimize this Java code for Spring Boot microservice:\n{java_code}"""

        payload = {"model": "llama3:8b", "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        result = response.json()
        return jsonify({"optimized": result.get("response")})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- Main ---
if __name__ == "__main__":
    if os.path.exists(EXCEL_FILE_PATH):
        pairs = extract_from_excel(EXCEL_FILE_PATH)
        store_in_vector_db(pairs)

    app.run(port=5000, debug=True)
