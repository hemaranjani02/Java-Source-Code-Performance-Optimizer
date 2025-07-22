from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
from sentence_transformers import SentenceTransformer
import chromadb
import traceback
import os
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://localhost:11434/api/generate"
EXCEL_FILE_PATH = os.path.join("backend", "FinalDataset.xlsx")

# Initialize model and ChromaDB
model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_store_test")
collection = client.get_or_create_collection("java_feedback_collection")

# --- 1. Read Excel (all sheets) and extract only obs and rec ---
def extract_from_excel(excel_path):
    print("\n--- Excel Reading ---", flush=True)
    all_sheets = pd.read_excel(excel_path, sheet_name=None)
    pairs = []

    for sheet_name, df in all_sheets.items():
        print(f"Reading sheet: {sheet_name}", flush=True)

        if "Observation" in df.columns and "Recommendation" in df.columns:
            df = df.dropna(subset=["Observation", "Recommendation"])

            for _, row in df.iterrows():
                obs = row["Observation"]
                rec = row["Recommendation"]
                pairs.append((obs, rec))
        else:
            print(f"❌ Skipped sheet '{sheet_name}' — required columns missing", flush=True)

    print(f"\n✅ Total pairs extracted: {len(pairs)}", flush=True)
    return pairs


# --- 2. Store in Chroma Vector DB ---
def store_in_vector_db(pairs):
    print("Sample pair from Excel:", pairs[0], flush=True)
    print("Sample pair from Excel:", pairs[1], flush=True)
    print(">>> Entered store_in_vector_db()", flush=True)

    try:
        for i, (obs, rec) in enumerate(pairs):
            embedding = model.encode(obs)
            unique_id = f"obs_{i}"
            print(f"🟡 Adding ID: {unique_id}", flush=True)
            print(f"Observation: {obs[:60]}", flush=True)

            try:
                collection.add(
                    documents=[obs],
                    metadatas=[{"recommendation": rec}],
                    ids=[unique_id],
                    embeddings=[embedding.tolist()]
                )
                print(f"✅ Added: {unique_id}", flush=True)
            except Exception as add_error:
                print(f"❌ Failed to add {unique_id}: {add_error}", flush=True)
                traceback.print_exc()

        count = collection.count()
        print(f"✅ Total records in collection: {count}", flush=True)

    except Exception as e:
        print(f"❌ Error in store_in_vector_db: {e}", flush=True)
        traceback.print_exc()


# --- 3. Retrieve relevant feedback ---
def get_relevant_observations(code):
    embedding = model.encode(code).tolist()
    results = collection.query(query_embeddings=[embedding], n_results=3)
    return [(doc, meta["recommendation"]) for doc, meta in zip(results["documents"][0], results["metadatas"][0])]


# --- 4. Java Optimization Endpoint ---
@app.route("/optimize-java", methods=["POST"])
def optimize_java():
    data = request.json
    java_code = data.get("code")
    if not java_code:
        return jsonify({"error": "No code provided"}), 400

    try:
        context_pairs = get_relevant_observations(java_code)

        context_str = "\n\n".join([
            f"Observation: {obs}\nRecommendation: {rec}"
            for obs, rec in context_pairs
        ])

        prompt = f"""Based on the following Observations and Recommendations:\n{context_str}\n\nPerformance Optimize this Java code for Spring Boot microservice:\n{java_code}"""

        payload = {"model": "llama3:8b", "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        result = response.json()

        return jsonify({
            "optimized": result.get("response"),
            "context_used": [{"observation": obs, "recommendation": rec} for obs, rec in context_pairs]
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/print-test")
def print_test():
    print(">>> PRINT TEST WORKING", flush=True)
    return "Check your console for the print message"


if __name__ == "__main__":
    with app.app_context():
        try:
            pairs = extract_from_excel(EXCEL_FILE_PATH)
            store_in_vector_db(pairs)
            print(f"✅ Total records in collection: {collection.count()}", flush=True)
        except Exception as e:
            print(f"❌ Error during data load: {e}", flush=True)
            traceback.print_exc()

    app.run(debug=True, use_reloader=False)
