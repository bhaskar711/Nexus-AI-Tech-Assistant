import json
import docx2txt

file_path = r"Knowledge\Smartphones info.docx"

text = docx2txt.process(file_path)

print("Document loaded successfully!")
print("Total characters:", len(text))

decoder = json.JSONDecoder()

objects = []
position = 0

while position < len(text):

    while position < len(text) and text[position].isspace():
        position += 1

    if position >= len(text):
        break

    try:
        data, end_position = decoder.raw_decode(text, position)
        objects.append(data)
        position = end_position

    except json.JSONDecodeError:
        position += 1


print("JSON objects found:", len(objects))


documents = []


def process_concept(category, subcategory, concept_name, concept_data):

    if not isinstance(concept_data, dict):
        return

    content_parts = []

    content_parts.append(f"Category: {category}")
    content_parts.append(f"Subcategory: {subcategory}")
    content_parts.append(f"Topic: {concept_name}")

    for key, value in concept_data.items():

        if key == "sources":
            continue

        if isinstance(value, list):

            if value:
                content_parts.append(
                    f"{key.replace('_', ' ').title()}: "
                    + "; ".join(str(item) for item in value)
                )

        elif isinstance(value, dict):

            content_parts.append(
                f"{key.replace('_', ' ').title()}: {json.dumps(value, ensure_ascii=False)}"
            )

        else:

            content_parts.append(
                f"{key.replace('_', ' ').title()}: {value}"
            )

    sources = concept_data.get("sources", [])

    if sources:
        content_parts.append("Sources:")

        for source in sources:

            if isinstance(source, dict):

                source_name = source.get("source_name", "")
                source_url = source.get("source_url", "")

                content_parts.append(
                    f"- {source_name}: {source_url}"
                )

    documents.append({
        "topic": f"{category} → {subcategory} → {concept_name}",
        "content": "\n".join(content_parts)
    })


for data in objects:

    if not isinstance(data, dict):
        continue

    category = data.get("category", "Unknown")
    subcategory = data.get("subcategory", "Unknown")

    for section_name, section_data in data.items():

        if section_name in [
            "category",
            "subcategory",
            "region",
            "research_date"
        ]:
            continue

        if not isinstance(section_data, dict):
            continue

        for concept_name, concept_data in section_data.items():

            process_concept(
                category,
                subcategory,
                concept_name,
                concept_data
            )


print("Final RAG documents:", len(documents))


print("\nFirst 3 RAG documents:\n")

for i, document in enumerate(documents[:3], start=1):

    print(f"========== DOCUMENT {i} ==========")
    print("TOPIC:")
    print(document["topic"])

    print("\nCONTENT:")
    print(document["content"])

    print("\n")
    
with open("rag_chunks.json", "w", encoding="utf-8") as file:
    json.dump(documents, file, ensure_ascii=False, indent=2)

print("RAG dataset saved successfully!")
print("File: rag_chunks.json")