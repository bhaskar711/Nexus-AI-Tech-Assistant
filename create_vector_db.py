import json
import faiss
import numpy as np

# Load embedded documents
with open("embedded_chunks.json", "r", encoding="utf-8") as file:
    documents = json.load(file)

print("Embedded documents loaded:", len(documents))

# Convert embeddings into NumPy array
embeddings = np.array(
    [document["embedding"] for document in documents],
    dtype="float32"
)

print("Embedding shape:", embeddings.shape)

# Create FAISS index
dimension = embeddings.shape[1]

index = faiss.IndexFlatL2(dimension)

# Add embeddings to the index
index.add(embeddings)

print("FAISS index created successfully!")
print("Vectors stored:", index.ntotal)

# Save FAISS index
faiss.write_index(index, "nexus.index")

print("Vector index saved as: nexus.index")

# Save document information separately
with open("nexus_documents.json", "w", encoding="utf-8") as file:
    json.dump(
        documents,
        file,
        ensure_ascii=False,
        indent=2
    )

print("Document data saved as: nexus_documents.json")