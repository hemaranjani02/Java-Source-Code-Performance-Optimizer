from sentence_transformers import SentenceTransformer
import chromadb
import traceback

model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_store")
collection = client.get_or_create_collection("java_feedback")

obs = "Test observation for chromaDB"
rec = "Test recommendation"
embedding = model.encode(obs)

try:
    print("Before add without embeddings", flush=True)
    collection.add(
        documents=[obs],
        metadatas=[{"recommendation": rec}],
        ids=["test_id_no_embedding"]
    )
    print("After add without embeddings", flush=True)
except Exception as e:
    print(f"Exception occurred: {e}", flush=True)
    traceback.print_exc()

