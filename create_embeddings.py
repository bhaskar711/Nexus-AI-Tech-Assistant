import json
import ollama

# Load RAG documents
with open("rag_chunks.json", "r", encoding="utf-8") as file:
    documents = json.load(file)

print("RAG documents loaded:", len(documents))

embedded_documents = []

for i, document in enumerate(documents, start=1):

    print(f"Embedding document {i}/{len(documents)}...")

    response = ollama.embed(
        model="nomic-embed-text",
        input=document["content"]
    )

    embedding = response["embeddings"][0]

    embedded_documents.append({
        "topic": document["topic"],
        "content": document["content"],
        "embedding": embedding
    })

# Save embeddings
with open("embedded_chunks.json", "w", encoding="utf-8") as file:
    json.dump(
        embedded_documents,
        file,
        ensure_ascii=False,
        indent=2
    )

print("\nEmbedding generation completed!")
print("Total embedded documents:", len(embedded_documents))
print("Embedding dimensions:", len(embedded_documents[0]["embedding"]))
print("Saved to: embedded_chunks.json")