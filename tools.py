import json
import ollama
import numpy as np


# ============================================================
# LOAD NEXUS KNOWLEDGE BASE
# ============================================================

with open(
    "embedded_chunks.json",
    "r",
    encoding="utf-8"
) as file:

    documents = json.load(file)


# ============================================================
# KNOWLEDGE SEARCH TOOL
# ============================================================

def search_knowledge(question, top_k=3):

    response = ollama.embed(
        model="nomic-embed-text",
        input=question
    )

    query_embedding = np.array(
        response["embeddings"][0],
        dtype="float32"
    )

    results = []

    for document in documents:

        document_embedding = np.array(
            document["embedding"],
            dtype="float32"
        )

        similarity = np.dot(
            query_embedding,
            document_embedding
        ) / (
            np.linalg.norm(query_embedding)
            *
            np.linalg.norm(document_embedding)
        )

        results.append({
            "topic": document["topic"],
            "content": document["content"],
            "similarity": float(similarity)
        })

    results.sort(
        key=lambda x: x["similarity"],
        reverse=True
    )

    return results[:top_k]