import json
import ollama
import numpy as np

# Load embedded documents
with open("embedded_chunks.json", "r", encoding="utf-8") as file:
    documents = json.load(file)

print("Documents loaded:", len(documents))


# Ask the user for a question
question = input("\nEnter your question: ")


# Create embedding for the question
response = ollama.embed(
    model="nomic-embed-text",
    input=question
)

query_embedding = np.array(
    response["embeddings"][0],
    dtype="float32"
)


# Calculate similarity with every document
results = []

for document in documents:

    document_embedding = np.array(
        document["embedding"],
        dtype="float32"
    )

    similarity = np.dot(query_embedding, document_embedding) / (
        np.linalg.norm(query_embedding) *
        np.linalg.norm(document_embedding)
    )

    results.append({
        "topic": document["topic"],
        "content": document["content"],
        "similarity": float(similarity)
    })


# Sort by similarity
results.sort(
    key=lambda x: x["similarity"],
    reverse=True
)


# Show the top 3 results
print("\nMost relevant documents:\n")

for i, result in enumerate(results[:3], start=1):

    print(f"========== RESULT {i} ==========")
    print("Similarity:", result["similarity"])
    print("Topic:", result["topic"])
    print("\nContent:")
    print(result["content"])
    print()