from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
from sentence_transformers import SentenceTransformer
import chromadb
import traceback
import os
import time

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://localhost:11434/api/generate"
EXCEL_FILE_PATH = os.path.join("backend", "Performence_Best_Practices.xlsx")

# Initialize shared components
model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_store")
collection = client.get_or_create_collection("java_feedback")

# 1. Read Excel and return (observation, recommendation) pairs
def extract_from_excel(excel_path):
    print(f"DEBUG: Reading Excel file at {excel_path}")
    df = pd.read_excel(excel_path)

    print("DEBUG: Excel columns:", df.columns.tolist())  # Show all column names

    # Check for specific content if column exists
    if "Observation" in df.columns and "Recommendation" in df.columns:
        df = df.dropna(subset=["Observation", "Recommendation"])
        print(f"DEBUG: Extracted {len(df)} rows with Observation and Recommendation")
        print("DEBUG: Sample row:")
        print(df[["Observation", "Recommendation"]].head(1))
        return list(zip(df["Observation"], df["Recommendation"]))
    else:
        print("ERROR: 'Observation' or 'Recommendation' column missing.")
        return []


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
    print(f"DEBUG: Encoding provided Java code for similarity search...")
    embedding = model.encode(code).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=3)

    print("DEBUG: Top 3 matches:")
    for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        print(f"\nResult #{i+1}")
        print(f"Observation: {doc}")
        print(f"Recommendation: {meta['recommendation']}")

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
        print(f"{context_str}")
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