from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
from sentence_transformers import SentenceTransformer
import chromadb
import traceback
import os
import Levenshtein

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://localhost:11434/api/generate"
# EXCEL_FILE_PATH = os.path.join("backend", "FinalDataset.xlsx")
EXCEL_FILE_PATH = os.path.abspath(os.path.join("backend", "FinalDataset.xlsx"))


model = SentenceTransformer("all-MiniLM-L6-v2")
# client = chromadb.Client()  # no path argument means in-memory only
try:
    client = chromadb.PersistentClient(path="./chroma_store1")
    collection = client.get_or_create_collection("java_feedback")
    print("Using persistent ChromaDB storage.")
except Exception as e:
    print(f"Persistent storage failed, falling back to in-memory client: {e}")
    traceback.print_exc()
    client = chromadb.Client()
    collection = client.get_or_create_collection("java_feedback")
    print("Using in-memory ChromaDB client.")

OBS_KEYS = ["Scenarios", "Observation", "Dependencies / Checklists", "Checklist", "Recommendation", "Section"]
REC_KEYS = ["Sample Code", "Recommendation / Sample Code", "Sample Config", "Conclusion", "Example", "Details"]
THRESHOLD = 0.7

def normalize_header(h):
    return h.strip().lower().replace("/", " ").replace("-", " ").replace("_", " ")

def fuzzy_match(col, keys):
    col = normalize_header(col)
    keys = [normalize_header(k) for k in keys]
    return max((Levenshtein.ratio(col, k) for k in keys), default=0)

def find_column(df, keys):
    best_col = None
    best_score = 0
    for col in df.columns:
        score = fuzzy_match(str(col), keys)
        if score > best_score and score >= THRESHOLD:
            best_col = col
            best_score = score
    return best_col

def extract_from_excel(excel_path):
    all_pairs = []
    try:
        xls = pd.ExcelFile(excel_path)
        for sheet in xls.sheet_names:
            try:
                df = xls.parse(sheet)
                obs_col = find_column(df, OBS_KEYS)
                rec_col = find_column(df, REC_KEYS)
                desc_col = "Description" if "Description" in df.columns else None

                if obs_col and rec_col:
                    cols = [obs_col, rec_col] + ([desc_col] if desc_col else [])
                    df = df[cols].dropna(subset=[obs_col, rec_col])
                    for _, row in df.iterrows():
                        obs = str(row[obs_col])
                        rec = str(row[rec_col])
                        desc = str(row[desc_col]) if desc_col else ""
                        all_pairs.append((obs, rec, sheet, desc))
            except Exception as e:
                print(f"Error parsing sheet '{sheet}': {e}")
                traceback.print_exc()
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        traceback.print_exc()
    return all_pairs

def store_in_vector_db(pairs):
    print(f"Storing {len(pairs)} pairs into vector DB...")
    for i, (obs, rec, sheet, desc) in enumerate(pairs):
        try:
            embedding = model.encode(obs)
            collection.add(
                documents=[obs],
                metadatas=[{
                    "recommendation": rec,
                    "sheet": sheet,
                    "description": desc
                }],
                ids=[f"obs_{i}"],
                embeddings=[embedding.tolist()]
            )
            if i % 5 == 0:
                print(f"Stored {i+1}/{len(pairs)} pairs...")
        except Exception as e:
            print(f"Failed to store embedding for pair {i}: {e}")
            traceback.print_exc()
    print("Finished storing pairs.")


def get_relevant_observations(code):
    try:
        embedding = model.encode(code).tolist()
        results = collection.query(query_embeddings=[embedding], n_results=3)
        return [(doc,
                 meta["recommendation"],
                 meta.get("sheet", "N/A"),
                 meta.get("description", ""))
                for doc, meta in zip(results["documents"][0], results["metadatas"][0])]
    except Exception as e:
        print("Error querying vector DB:", e)
        traceback.print_exc()
        return []

@app.route("/optimize-java", methods=["POST"])
def optimize_java():
    try:
        data = request.json
        java_code = data.get("code")
        if not java_code:
            return jsonify({"error": "No code provided"}), 400

        context_pairs = get_relevant_observations(java_code)
        if not context_pairs:
            return jsonify({"error": "No relevant observations found."}), 404

        context_str = "\n\n".join([
            f"Sheet: {sheet}\nObservation: {obs}\nDescription: {desc}\nRecommendation: {rec}"
            for obs, rec, sheet, desc in context_pairs
        ])

        prompt = f"""Based on the following Observations and Recommendations:\n{context_str}\n\nPerformance Optimize this Java code for Spring Boot microservice:\n{java_code}"""

        payload = {"model": "llama3:8b", "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)

        if response.status_code != 200:
            return jsonify({"error": f"LLM service failed: {response.text}"}), 500

        result = response.json()
        return jsonify({"optimized": result.get("response")})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("Script started")
    try:
        print("Checking collection count...")
        count = collection.count()
        print(f"Collection count: {count}")

        if count == 0:
            print("Collection empty, loading data...")
            pairs = extract_from_excel(EXCEL_FILE_PATH)
            print(f"Extracted {len(pairs)} pairs")
            store_in_vector_db(pairs)
            print("Data loaded into ChromaDB.")
        else:
            print("ChromaDB already has data.")

    except Exception as e:
        print("Error during startup:", e)
        traceback.print_exc()

    print("Calling app.run()...")
    app.run(debug=True)

