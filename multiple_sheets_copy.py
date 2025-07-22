from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
from sentence_transformers import SentenceTransformer
import chromadb
import traceback
import os
import logging

# Setup Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://localhost:11434/api/generate"
EXCEL_FILE_PATH = os.path.join("backend", "FinalDataset.xlsx")

# Initialize model and ChromaDB
try:
    logging.info("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    logging.info("Model loaded successfully.")
except Exception as e:
    logging.error("❌ Failed to load embedding model.")
    traceback.print_exc()
    raise e

try:
    logging.info("Initializing ChromaDB client...")
    client = chromadb.Client()
    #client.delete_collection("java_feedback")
    #collection = client.get_or_create_collection("java_feedback")
    collection = client.get_or_create_collection("java_feedback")
    logging.info("ChromaDB client initialized.")
except Exception as e:
    logging.error("❌ Failed to initialize ChromaDB.")
    traceback.print_exc()
    raise e

# 1. Read Excel (all sheets) and return (observation, recommendation) pairs
def extract_from_excel(excel_path):
    logging.info(f"Reading Excel from: {excel_path}")
    pairs = []
    try:
        all_sheets = pd.read_excel(excel_path, sheet_name=None)
        for sheet_name, df in all_sheets.items():
            logging.debug(f"Processing sheet: {sheet_name}")
            if "Observation" in df.columns and "Recommendation" in df.columns:
                df = df.dropna(subset=["Observation", "Recommendation"])
                for _, row in df.iterrows():
                    pairs.append((row["Observation"], row["Recommendation"]))
            else:
                logging.warning(f"Sheet '{sheet_name}' skipped — missing required columns.")
        logging.info(f"✅ Total pairs extracted: {len(pairs)}")
        return pairs
    except FileNotFoundError:
        logging.error(f"❌ Excel file not found at: {excel_path}")
        return []
    except Exception as e:
        logging.error("❌ Error while reading Excel.")
        traceback.print_exc()
        return []

# 2. Embed and store in ChromaDB
def store_in_vector_db(pairs, batch_size=51):
    logging.info("📦 Starting data store into ChromaDB...")
    success_count = 0

    try:
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i + batch_size]
            valid_batch = [(obs, rec) for obs, rec in batch if obs and rec]
            if not valid_batch:
                continue

            docs = [obs for obs, _ in valid_batch]
            metas = [{"recommendation": rec} for _, rec in valid_batch]
            ids = [f"obs_{i + j}" for j in range(len(valid_batch))]

            try:
                embeddings = model.encode(docs)
                logging.debug(f"Documents in batch: {docs}")
                logging.debug(f"IDs in batch: {ids}")
                logging.debug(f"Embeddings shape: {[len(e) for e in embeddings]}")

                collection.upsert(
                    documents=docs,
                    metadatas=metas,
                    ids=ids,
                    embeddings=[emb.tolist() for emb in embeddings]
                )
                success_count += len(valid_batch)
                logging.info(f"✅ Stored batch {i // batch_size + 1}: {len(valid_batch)} records.")
            except Exception as batch_err:
                logging.error(f"❌ Failed to store batch at index {i}: {batch_err}")
                traceback.print_exc()

        logging.info(f"✅ Finished storing. Total successful records: {success_count}")
        logging.info(f"🔢 Total records in Chroma collection after insert: {collection.count()}")
    except Exception as e:
        logging.error("❌ Unexpected error during storing to ChromaDB.")
        traceback.print_exc()


# 3. Search relevant observation by code
def get_relevant_observations(code):
    try:
        embedding = model.encode(code).tolist()
        results = collection.query(query_embeddings=[embedding], n_results=3)

        if not results or not results["documents"]:
            logging.warning("⚠️ No relevant documents found.")
            return []

        return [(doc, meta["recommendation"]) for doc, meta in zip(results["documents"][0], results["metadatas"][0])]
    except Exception as e:
        logging.error("❌ Error during ChromaDB query.")
        traceback.print_exc()
        return []

# --- Java Route ---
@app.route("/optimize-java", methods=["POST"])
def optimize_java():
    try:
        data = request.json
        java_code = data.get("code", "").strip()
        if not java_code:
            return jsonify({"error": "No code provided"}), 400

        context_pairs = get_relevant_observations(java_code)
        context_str = "\n\n".join([f"Observation: {obs}\nRecommendation: {rec}" for obs, rec in context_pairs])

        prompt = f"""Based on the following Observations and Recommendations:\n{context_str}\n\nPerformance Optimize this Java code for Spring Boot microservice:\n{java_code}"""

        payload = {"model": "llama3:8b", "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)

        if response.status_code != 200:
            return jsonify({"error": "Model API error", "details": response.text}), 502

        result = response.json()
        return jsonify({
            "optimized": result.get("response"),
            "context_used": [{"observation": obs, "recommendation": rec} for obs, rec in context_pairs]
        })

    except Exception as e:
        logging.error("❌ Error in /optimize-java route.")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- Main ---
if __name__ == "__main__":
    logging.info("✅ Starting Flask backend...")

    if os.path.exists(EXCEL_FILE_PATH):
        try:
            pairs = extract_from_excel(EXCEL_FILE_PATH)
            if pairs:
                store_in_vector_db(pairs)
            else:
                logging.warning("⚠️ No valid data extracted from Excel.")
        except Exception as e:
            logging.error("❌ Critical failure during data preloading.")
            traceback.print_exc()
    else:
        logging.error("❌ Excel file does not exist. Please check the path.")

    app.run(port=5000, debug=True)
