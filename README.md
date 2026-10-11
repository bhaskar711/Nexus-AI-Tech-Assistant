# Nexus — AI-Powered Technology Information Assistant

Nexus is a Python-based, command-line AI assistant designed to help users explore technology-related topics, including smartphones, laptops, processors, GPUs, computer components, operating systems, and consumer electronics.

The project combines a local Large Language Model (LLM) with web-based information retrieval and Retrieval-Augmented Generation (RAG) to support technology question answering.

## Features

- **AI-powered conversations:** Uses Ollama to run a local language model.
- **Technology assistance:** Answers questions about consumer technology and computer hardware.
- **Web research:** Includes web-search and research components for retrieving online information.
- **Smartphone specifications:** Provides a dedicated module for retrieving smartphone specification information.
- **Retrieval-Augmented Generation (RAG):** Uses a local knowledge base and FAISS-based vector search to retrieve relevant information.
- **Modular architecture:** Separates the chatbot, research tools, smartphone specification logic, and knowledge retrieval components.

## Technologies Used

- Python
- Ollama
- Large Language Models (LLMs)
- Retrieval-Augmented Generation (RAG)
- FAISS
- NumPy
- Beautiful Soup
- Requests

## Project Structure

| File | Purpose |
|---|---|
| `app.py` | Command-line chatbot interface |
| `agent.py` | AI agent and query-handling logic |
| `phone_specs.py` | Smartphone specification retrieval |
| `you_search_tool.py` | Web-search functionality |
| `web_research.py` | Web research utilities |
| `verifier.py` | Verification-related logic |
| `tools.py` | Knowledge retrieval tools |
| `nexus_rag.py` | RAG functionality |
| `vector_search.py` | Vector search functionality |
| `requirements.txt` | Python dependency list |
| `.gitignore` | Excludes selected local and sensitive files |

Additional scripts support dataset preparation, document chunking, embedding generation, and vector database creation.

## Prerequisites

- Python installed on your computer
- Ollama installed and running locally
- The language model required by the application
- Any API credentials required by the configured web-search provider

## Getting Started

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd Nexus-AI-Tech-Assistant
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with the HTTPS URL of this repository.

### 2. Install the dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Set up Ollama

Install Ollama from [https://ollama.com/](https://ollama.com/) and download the model used by the application:

```bash
ollama pull qwen3.5:4b
```

Ensure Ollama is running before starting the chatbot.

### 4. Configure environment variables

If the application requires API keys, create a local `.env` file and configure the variables expected by the project.

**Do not publish your `.env` file or API keys to GitHub.**

### 5. Run the command-line chatbot

```bash
python app.py
```

Enter a technology-related question at the `You:` prompt. Type `exit` or `quit` to stop the conversation.

## Project Goals

Nexus explores the practical integration of local language models, web research, and retrieval-based question answering in a technology-focused assistant.

## Current Scope

Nexus is a command-line application intended to run locally. It is not currently presented as a publicly deployed web application.

## Future Improvements

- Strengthen source verification and specification accuracy.
- Enhance the user interface and overall user experience.
- Expand the knowledge base and automated testing.

## Author

Developed as a personal AI/ML project to explore practical applications of LLMs, web retrieval, and RAG.
