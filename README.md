# RAG App

[![GitHub Release](https://img.shields.io/github/v/release/talacjos/rag-app?style=flat-square)](https://github.com/jotalac/rag-app/releases/latest)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)](https://github.com/python/cpython)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-FF4F00?style=flat&logo=databricks&logoColor=white)](https://github.com/chroma-core/chroma)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat&logo=langchain&logoColor=white)](https://github.com/langchain-ai/langchain)
[![Textual](https://img.shields.io/badge/Textual-000000?style=flat&logo=terminal&logoColor=white)](https://github.com/Textualize/textual)
[![uv](https://img.shields.io/badge/uv-DE5FE9?style=flat&logo=rust&logoColor=white)](https://github.com/astral-sh/uv)

A pure RAG pipeline with TUI, designed to work well with smaller local LLMs (via Ollama). 

## Overview

- This project is a streamlined RAG application.
- By sticking to a pure RAG pipeline, this app works well with smaller models, such as `llama3.2:3b`.
- Smaller models don't handle agentic workflows and tool calling very well; they often get stuck in a loop or make things up.
- With this app you get answers referencing only the uploaded documents. When the information is not there, the app will tell you instead of making things up.

## Requirements

- **Python:** 3.14 or newer.
- **Package Manager:** [uv](https://github.com/astral-sh/uv) (recommended for dependency management).
- **LLM Engine:** [Ollama](https://docs.ollama.com/linux) installed and running locally. 
  - Make sure Ollama is running (e.g., `ollama serve`). Ideally, configure it to autostart on boot.
  - You need to download an LLM (e.g., `ollama pull llama3.2:3b`) and an embedding model (e.g., `ollama pull nomic-embed-text`).
  - Run `ollama ls` to verify that the models are downloaded.

## Installation
### Install Globally with UV
```bash
uv tool install git+https://github.com/jotalac/rag-app.git
```

### Alternative
1. **Clone the repository:**
   ```bash
   git clone https://github.com/jotalac/rag-app.git
   cd rag-app
   ```

2. **Install app:**
   ```bash
   uv tool install .
   ```

### Updating the App

**If you installed globally via Git:**
Simply run the upgrade command:
```bash
uv tool upgrade rag-app
```

**If you installed via local clone (Alternative):**
Pull the latest code first, then upgrade:
```bash
git pull
uv tool install . --force
```

## Usage

Start the TUI by running:
```bash
rag-app
```

> **Note on Cold Starts:** The first generation query is always slow because Ollama needs to load the model into memory. This delay also occurs anytime you change the model in the configuration.

- In the app, run `/help` to see all available options.
- `ctrl+p` open the default menu, where you can change theme or do other actions

### Adding resources (in TUI)

- Create a folder anywhere on your device where all your resources will be stored.
- In the TUI config dialog (`/config`), set the *resources directory* to your created folder.
- Run `/add-resources file1 file2 ...` or `/add-resources-dir dir_name` to embed the files into the vector database.
- After the files are embedded, you can safely delete them from the directory.

### Asking about resources
- Type your prompt in the input, and the app will automatically look at the uploaded resources.
- Smaller models might struggle if the resources are not in English.
- If no relevant data is retrieved from the vector database, generation won't start, and you will see a warning message.

## Current Limitations

- **Single Workspace:** You cannot separate your resources; all resources are available for all prompts.
- **Language Support:** For smaller models, querying in languages other than English often yields poor or hallucinated results.
- **Thinking Models:** Thinking output is not currently visible.


## Roadmap & To-do

- Add support for importing resources directly from URLs.
- Add support for embedding and querying images, audio, and other media resources.
- Add support for cloud LLM providers.
- Adding resources from any folder (not only from one resources directory)
