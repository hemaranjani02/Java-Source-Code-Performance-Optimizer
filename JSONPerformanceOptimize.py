from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
import json
from sentence_transformers import SentenceTransformer
import chromadb
import traceback
import os

app = Flask(__name__)
CORS(app)

# Constants
OLLAMA_URL = "http://localhost:11434/api/generate"
EXCEL_FILE_PATH = os.path.join("backend", "Performence_Best_Practices.xlsx")
JSON_FILE_PATH = os.path.join("backend", "DataSet.json")

# Initialize Chroma and model
model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_store")
collection = client.get_or_create_collection("java_feedback")

# 1. Extract Excel (Observation/Recommendation)
def extract_from_excel(excel_path):
    df = pd.read_excel(excel_path)
    df = df.dropna(subset=["Observation", "Recommendation"])
    return list(zip(df["Observation"], df["Recommendation"]))

# 2. Extract and flatten JSON into (text, tag) chunks
def flatten_json(json_data, namespace=""):
    chunks = []

    def recurse(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                recurse(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                recurse(item, f"{path}[{i}]")
        else:
            key = path if path else namespace
            chunks.append((f"{key}: {obj}", key))

    recurse(json_data)
    return chunks

# 3. Store Excel + JSON data in ChromaDB
def store_all_to_vector_db(excel_pairs, json_chunks):
    # Excel embeddings
    for i, (obs, rec) in enumerate(excel_pairs):
        embedding = model.encode(obs)
        collection.add(
            documents=[obs],
            metadatas=[{"recommendation": rec, "source": "excel"}],
            ids=[f"obs_{i}"],
            embeddings=[embedding.tolist()]
        )

    # JSON embeddings
    for j, (text, key) in enumerate(json_chunks):
        embedding = model.encode(text)
        collection.add(
            documents=[text],
            metadatas=[{"recommendation": None, "source": "json", "key": key}],
            ids=[f"json_{j}"],
            embeddings=[embedding.tolist()]
        )

# 4. Query ChromaDB for relevant entries
def get_relevant_context(user_input, top_k=4):
    embedding = model.encode(user_input).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=top_k)
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    context_blocks = []
    for doc, meta in zip(docs, metas):
        if meta["source"] == "excel":
            context_blocks.append(f"Observation: {doc}\nRecommendation: {meta['recommendation']}")
        elif meta["source"] == "json":
            context_blocks.append(f"Tech Context ({meta['key']}): {doc}")
    return "\n\n".join(context_blocks)

# 5. Optimize Java code using combined context + Ollama
@app.route("/optimize-java", methods=["POST"])
def optimize_java():
    data = request.json
    java_code = data.get("code")
    if not java_code:
        return jsonify({"error": "No code provided"}), 400

    try:
        context = get_relevant_context(java_code)
        prompt = f"""Use the following context excel and JSON content to improve the given code:

{context}

Now optimize the following Java Spring Boot microservice code:

{java_code}
"""

        payload = {"model": "llama3:8b", "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        result = response.json()
        return jsonify({"optimized": result.get("response")})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- Run server and load knowledge base ---
if __name__ == "__main__":
    try:
        if os.path.exists(EXCEL_FILE_PATH):
            excel_pairs = extract_from_excel(EXCEL_FILE_PATH)
        else:
            excel_pairs = []

        if os.path.exists(JSON_FILE_PATH):
            with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            json_chunks = flatten_json(json_data)
        else:
            json_chunks = []

        store_all_to_vector_db(excel_pairs, json_chunks)
        print("✅ Knowledge base loaded successfully.")
    except Exception as e:
        print(f"❌ Failed to load knowledge base: {e}")

    app.run(port=5000, debug=True)
