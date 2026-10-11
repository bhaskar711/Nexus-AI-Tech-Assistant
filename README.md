# Nexus — GenAI-Powered Smartphone Specification Assistant

Nexus is a **Generative AI (GenAI) project** designed to help users find smartphone specifications through a conversational command-line interface.

The project combines Large Language Models (LLMs), web-based information retrieval, and Retrieval-Augmented Generation (RAG) techniques to support smartphone-related question answering.

Its primary goal is to retrieve relevant smartphone information and present specifications clearly, with particular emphasis on four essential areas:

- **Display** — screen technology, size, resolution, refresh rate, and other available display details.
- **Processor** — chipset and processor-related information.
- **Camera** — rear and front camera specifications and supported features.
- **Battery & Charging** — battery capacity, charging speed, and supported charging features.

Nexus is built with Python and uses Ollama for local language-model execution.

## Key Features

- **GenAI-Powered Conversations:** Uses a large language model to provide natural-language responses to smartphone-related queries.
- **Smartphone Specification Retrieval:** Includes a dedicated module for retrieving smartphone specifications.
- **Web Research:** Uses web-based research capabilities to find smartphone information.
- **Retrieval-Augmented Generation (RAG):** Includes components for retrieving relevant information from a knowledge base.
- **Semantic Search:** Uses embeddings and FAISS for vector-based information retrieval.
- **Core Specification Focus:** Prioritizes display, processor, camera, and battery and charging information.
- **Modular Architecture:** Separates the assistant logic, smartphone specification retrieval, web research, and RAG functionality into individual modules.
- **Local LLM Integration:** Uses Ollama to run the configured language model locally.

## How It Works

1. **User Query:** The user asks about a smartphone, its specifications, or a comparison.
2. **Query Processing:** Nexus processes the query and identifies the relevant smartphone or information request.
3. **Information Retrieval:** The relevant workflow retrieves information from available web sources or the local knowledge base.
4. **Response Generation:** The LLM helps organize the retrieved context into a readable response.
5. **Specification Presentation:** Nexus presents the available smartphone information, prioritizing display, processor, camera, and battery and charging details.

The information retrieval path depends on the query and the modules configured for that workflow.

## Technologies Used

| Technology | Purpose |
|---|---|
| Generative AI and LLMs | Natural-language response generation |
| Ollama | Local LLM execution |
| Retrieval-Augmented Generation (RAG) | Retrieval-supported question answering |
| FAISS | Vector similarity search |
| Embeddings | Semantic representation of text |
| Python | Application logic and integration |
| NumPy | Numerical operations on embeddings |
| Requests | HTTP requests for information retrieval |
| Beautiful Soup | HTML parsing and data extraction |

## Project Structure

```text
Nexus/
├── agent.py                  # Assistant logic and tool orchestration
├── app.py                    # Command-line chat interface
├── phone_specs.py            # Smartphone specification retrieval
├── tools.py                  # Tool-related functionality
├── you_search_tool.py        # Web search functionality
├── web_research.py           # Web research logic
├── verifier.py               # Verification-related functionality
├── nexus_rag.py              # RAG functionality
├── vector_search.py          # Vector-based retrieval
├── build_concept_rag.py      # RAG data preparation
├── build_rag_dataset.py      # RAG dataset construction
├── chunk_word.py             # Text chunking
├── structured_chunks.py      # Structured text processing
├── create_embeddings.py      # Embedding generation
├── create_vector_db.py       # Vector index creation
├── requirements.txt          # Python dependencies
└── .gitignore                # Git exclusions
```

Additional datasets, knowledge files, and generated vector indexes may be required for the corresponding retrieval workflows.

## Getting Started

### Prerequisites

- Python
- Ollama
- The language model configured by the application
- Any required data files and retrieval assets

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/Nexus-AI-Tech-Assistant.git
cd Nexus-AI-Tech-Assistant
```

Replace `YOUR-USERNAME` with your GitHub username.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Download the Language Model

```bash
ollama pull qwen3.5:4b
```

Ensure Ollama is running before starting a workflow that uses the local model.

### 4. Run the Command-Line Interface

```bash
python app.py
```

Enter a question in the terminal to interact with the basic chat interface. Type `exit` or `quit` to end the session.

Other modules may require their own configuration or execution steps.

## Security

- Never commit API keys, passwords, tokens, or `.env` files.
- Keep secrets in local environment variables or a `.env` file excluded by `.gitignore`.
- Configure any required external-service credentials locally.

## Project Status

- **Category:** Generative AI
- **Domain:** Smartphone specifications
- **Interface:** Command-line
- **LLM:** Ollama
- **Core components:** LLM-based responses, web research, RAG, and vector retrieval
- **Deployment:** Local execution; no public application deployment is claimed

## Project Objective

Nexus explores how Generative AI can be combined with web research and information retrieval to build a smartphone-focused assistant. The project emphasizes retrieving relevant specifications and presenting them clearly, with particular attention to display, processor, camera, and battery and charging information.

## Future Improvements

- Strengthen source verification and specification accuracy.
- Enhance the user interface and overall user experience.
- Expand the knowledge base and automated testing.

**Nexus — A GenAI-powered assistant for smartphone specifications.**
