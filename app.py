from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
from sentence_transformers import SentenceTransformer
import chromadb
# from chromadb.config import Settings
import traceback
import os

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://localhost:11434/api/generate"
EXCEL_FILE_PATH = "backend\Performence_Best_Practices.xlsx"  # <-- Update this with your actual Excel file path

# 1. Read Excel and return (observation, recommendation) pairs
def extract_from_excel(excel_path):
    df = pd.read_excel(excel_path)
    df = df.dropna(subset=["Observation", "Recommendation"])
    return list(zip(df["Observation"], df["Recommendation"]))

# 2. Embed and store in ChromaDB
def store_in_vector_db(pairs):
    client = chromadb.PersistentClient(path="./chroma_store")
    collection = client.get_or_create_collection("java_feedback")
    model = SentenceTransformer("all-MiniLM-L6-v2")

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
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embedding = model.encode(code).tolist()
    client = chromadb.PersistentClient(path="./chroma_store")
    collection = client.get_or_create_collection("java_feedback")
    results = collection.query(query_embeddings=[embedding], n_results=3)
    return [(doc, meta["recommendation"]) for doc, meta in zip(results["documents"][0], results["metadatas"][0])]

@app.route("/optimize-java", methods=["POST"])
def optimize_code():
    data = request.json
    java_code = data.get("code")

    if not java_code:
        return jsonify({"error": "No code provided"}), 400

    try:
        context_pairs = get_relevant_observations(java_code)
        context_str = "\n\n".join([f"Observation: {obs}\nRecommendation: {rec}" for obs, rec in context_pairs])

        prompt = f"""Based on the following Observations and Recommendations:\n{context_str}\n\n Performance Optimize this Java code for springboot microservice:\n{java_code}"""

        payload = {
            "model": "llama3:8b",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(OLLAMA_URL, json=payload)
        result = response.json()
        print(result)
        return jsonify({"optimized": result.get("response")})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    if os.path.exists(EXCEL_FILE_PATH):
        pairs = extract_from_excel(EXCEL_FILE_PATH)
        store_in_vector_db(pairs)

    app.run(port=5000, debug=True)
