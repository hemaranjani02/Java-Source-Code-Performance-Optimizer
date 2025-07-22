from sentence_transformers import SentenceTransformer
import chromadb
import traceback

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize Chroma DB
client = chromadb.PersistentClient(path="./chroma_store")
collection = client.get_or_create_collection("test_collection")

# Prepare test data
obs = "This is a test observation for embedding"
rec = "This is the recommended improvement"
sheet = "TestSheet"
test_id = "test_obs_001"

embedding = model.encode(obs).tolist()

# Try adding to Chroma DB
try:
    print("🟡 Adding test record...", flush=True)

    try:
        collection.add(
            documents=[obs],
            metadatas=[{"recommendation": rec, "sheet": sheet}],
            ids=[test_id],
            embeddings=[embedding]
        )
        print("✅ Test record added successfully", flush=True)
    except Exception as add_error:
        print(f"❌ Error inside add(): {add_error}", flush=True)
        traceback.print_exc()

    count = collection.count()
    print(f"📊 Total records in collection: {count}", flush=True)

except Exception as outer_error:
    print(f"❌ Outer failure: {outer_error}", flush=True)
    traceback.print_exc()

