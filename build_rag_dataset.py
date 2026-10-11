import json
import re
import docx2txt

file_path = r"Knowledge\Smartphones info.docx"

text = docx2txt.process(file_path)

print("Document loaded successfully!")
print("Total characters:", len(text))


# --------------------------------------------------
# STEP 1: Find major sections in the document
# --------------------------------------------------

section_pattern = re.compile(
    r"(?m)^([A-Z][A-Za-z0-9 ,&/()\-]+)$"
)

matches = list(section_pattern.finditer(text))

print("Possible section headings found:", len(matches))


# --------------------------------------------------
# STEP 2: Split document into meaningful sections
# --------------------------------------------------

sections = []

for i, match in enumerate(matches):

    title = match.group(1).strip()

    start = match.start()

    if i + 1 < len(matches):
        end = matches[i + 1].start()
    else:
        end = len(text)

    content = text[start:end].strip()

    if len(content) < 100:
        continue

    sections.append({
        "title": title,
        "content": content
    })


print("Candidate sections created:", len(sections))


# --------------------------------------------------
# STEP 3: Create RAG documents
# --------------------------------------------------

documents = []

for section in sections:

    content = section["content"]

    # Ignore extremely small fragments
    if len(content) < 200:
        continue

    documents.append({
        "topic": section["title"],
        "content": content
    })


# --------------------------------------------------
# STEP 4: Save dataset
# --------------------------------------------------

with open("rag_chunks_new.json", "w", encoding="utf-8") as file:

    json.dump(
        documents,
        file,
        ensure_ascii=False,
        indent=2
    )


print("\nRAG dataset created successfully!")
print("Total RAG documents:", len(documents))
print("Saved as: rag_chunks_new.json")


# --------------------------------------------------
# STEP 5: Show sample documents
# --------------------------------------------------

print("\n========== FIRST 10 DOCUMENTS ==========\n")

for i, document in enumerate(documents[:10], start=1):

    print(f"{i}. {document['topic']}")

print("\n========== SEARCH TEST ==========\n")

keywords = ["OIS", "Camera", "Processor", "Battery"]

for keyword in keywords:

    count = sum(
        keyword.lower() in document["content"].lower()
        for document in documents
    )

    print(f"{keyword}: found in {count} documents")