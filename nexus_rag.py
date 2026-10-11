import json
import ollama
import numpy as np


# ============================================================
# LOAD EMBEDDED KNOWLEDGE
# ============================================================

with open(
    "embedded_chunks.json",
    "r",
    encoding="utf-8"
) as file:

    documents = json.load(file)


print(
    "Nexus knowledge base loaded:",
    len(documents),
    "documents"
)


# ============================================================
# SEMANTIC SEARCH
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

        query_norm = np.linalg.norm(query_embedding)
        document_norm = np.linalg.norm(document_embedding)

        if query_norm == 0 or document_norm == 0:
            similarity = 0.0
        else:
            similarity = np.dot(
                query_embedding,
                document_embedding
            ) / (
                query_norm
                *
                document_norm
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


# ============================================================
# ASK NEXUS
# ============================================================

def ask_nexus(question):

    results = search_knowledge(
        question,
        top_k=3
    )


    # --------------------------------------------------------
    # CHECK WHETHER RETRIEVED KNOWLEDGE IS RELEVANT
    # --------------------------------------------------------

    similarity_threshold = 0.60

    relevant_results = [

        result

        for result in results

        if result["similarity"]
        >= similarity_threshold

    ]


    if not relevant_results:

        print(
            "\nNexus: I don't have enough information "
            "about this topic in my current knowledge base."
        )

        return


    # --------------------------------------------------------
    # BUILD CONTEXT
    # --------------------------------------------------------

    context = "\n\n".join(

        result["content"]

        for result in relevant_results

    )


    # --------------------------------------------------------
    # SEND CONTEXT TO QWEN
    # --------------------------------------------------------

    prompt = f"""
You are Nexus, a technology assistant.

Answer the user's question using the provided knowledge.

Knowledge:
{context}

User question:
{question}

Rules:

- Use the provided knowledge as the primary source.
- Do not invent specifications, numbers, dates or features.
- Do not introduce unsupported facts.
- Explain technical concepts simply.
- Assume the user may have zero technical knowledge.
- Explain important technical terms in simple language.
- Give a real-world example when the knowledge supports one.
- For comparisons, clearly explain the differences.
- If the provided knowledge does not contain enough information, say so.
- Do not mention the internal RAG system or embeddings.
"""


    response = ollama.chat(

        model="qwen3.5:4b",

        messages=[

            {
                "role": "user",
                "content": prompt
            }

        ],

        think=False,

        stream=True
    )


    # --------------------------------------------------------
    # STREAM ANSWER
    # --------------------------------------------------------

    print(
        "\nNexus: ",
        end="",
        flush=True
    )


    for chunk in response:

        text = chunk["message"]["content"]

        print(
            text,
            end="",
            flush=True
        )


    print()


# ============================================================
# STANDALONE RAG MODE
# ============================================================

def run_rag_chat():

    print("\nNexus RAG is ready!")
    print("Type 'exit' to stop.")


    while True:

        question = input("\nYou: ")


        if question.lower() in [
            "exit",
            "quit"
        ]:

            break


        if not question.strip():
            continue


        ask_nexus(question)


# ============================================================
# START STANDALONE RAG ONLY
# ============================================================

if __name__ == "__main__":

    run_rag_chat()