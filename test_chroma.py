import traceback
import chromadb

try:
    client = chromadb.PersistentClient(path="./chroma_store1")
    collection = client.get_or_create_collection("java_feedback")
    print("Client and collection created.")

    print("Calling collection.count()...")
    count = collection.count()
    print(f"Collection count: {count}")

except Exception as e:
    print("Error:", e)
    traceback.print_exc()
