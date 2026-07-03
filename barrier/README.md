# Barrier AI FAQ Assistant

A retrieval-augmented (RAG) chat assistant that answers questions about the [debauchee/barrier](https://github.com/debauchee/barrier) GitHub repository, grounded in its own Markdown documentation. Every answer is backed by citations linking directly back to the source files.

Built as part of ongoing AI engineering coursework, focused on hands-on RAG, agentic tool-calling, and deployment practice rather than a polished production product.

> This is one part of a larger monorepo tracking my AI engineering learning process — see the [root README](../README.md) for the full repository structure, including course exercises and practice notebooks.

## How it works

# Barrier AI FAQ Assistant

A retrieval-augmented (RAG) chat assistant that answers questions about the [debauchee/barrier](https://github.com/debauchee/barrier) GitHub repository, grounded in its own Markdown documentation. Every answer is backed by citations linking directly back to the source files.

Built as part of ongoing AI engineering coursework, focused on hands-on RAG, agentic tool-calling, and deployment practice rather than a polished production product.

> This is one part of a larger monorepo tracking my AI engineering learning process — see the [root README](../README.md) for the full repository structure, including course exercises and practice notebooks.

## 🔍 How it works

1. **Ingest** — downloads the target repository as a zip archive, extracts its Markdown documentation, and parses out frontmatter/content.
2. **Index** — builds a searchable text index over the documents using [minsearch](https://github.com/alexeygrigorev/minsearch).
3. **Search tool** — wraps the index as a callable tool, enriching each result with a direct GitHub citation URL.
4. **Agent** — a [pydantic-ai](https://ai.pydantic.dev/) agent, instructed to always search before answering and to cite every factual claim with a source link.
5. **UI** — a [Streamlit](https://streamlit.io/) chat interface, streaming responses token-by-token as the agent generates them.
6. **Logging** — every interaction is written to a local JSON log for later inspection and debugging.

## 🗂️ Project structure

```
barrier/
├── app.py            # Streamlit UI, chat loop, response streaming
├── ingest.py          # Repo download, document extraction, chunking, indexing
├── search_tools.py    # Search tool wrapper — queries the index, builds citation URLs
├── search_agent.py    # Agent configuration and system prompt
├── logs.py            # Conversation logging to JSON
├── pyproject.toml     # Dependencies (PEP 621 format, managed with uv)
└── README.md
```

## 🧰 Tech stack

- **LLM orchestration:** [pydantic-ai](https://ai.pydantic.dev/)
- **Search/indexing:** [minsearch](https://github.com/alexeygrigorev/minsearch)
- **Document parsing:** [python-frontmatter](https://python-frontmatter.readthedocs.io/)
- **UI:** [Streamlit](https://streamlit.io/)
- **LLM provider:** OpenAI (`gpt-4o-mini` by default)
- **Dependency management:** [uv](https://docs.astral.sh/uv/), `pyproject.toml`

## 🚀 Getting started

### Prerequisites

- Python 3.11+
- An OpenAI API key
- [uv](https://docs.astral.sh/uv/) installed

### Setup

1. Clone the repository and navigate into the project folder.

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Create a `.env` file in the project root with your API key:
   ```
   OPENAI_API_KEY=your-key-here
   ```

4. Run the app:
   ```bash
   uv run streamlit run app.py
   ```

The app will be available at `http://localhost:8501`. On first load, it will download and index the target repository — this may take a few seconds.

### Configuration

The target repository is currently set in `app.py`:

```python
REPO_OWNER = "debauchee"
REPO_NAME = "barrier"
```

Change these to point the assistant at a different repository's documentation. Note that if the repository has a very different file structure, you may want to revisit the (currently disabled) document filtering logic in `ingest.py`.

## ☁️ Deployment

This app is deployed on [Streamlit Community Cloud](https://streamlit.io/cloud). A few environment-specific notes if you're deploying your own copy:

- Streamlit Cloud installs dependencies via Poetry when it detects a `pyproject.toml`. Since this project doesn't need to be installed as a package, `package-mode = false` is set under `[tool.poetry]` to avoid installation errors.
- `st.cache_resource` is used to ensure the (relatively expensive) ingestion and agent setup only runs once per app process, not on every user interaction.
- Logs written by `logs.py` are **not persisted** on Streamlit Cloud — the local filesystem is ephemeral and gets wiped on every restart/redeploy. Logging is primarily useful for local development in its current form.

## 🧭 Roadmap

- [ ] **Evaluations** — automated eval suite to measure retrieval quality and answer correctness/citation accuracy against a set of reference questions (in progress).
- [ ] Persist logs somewhere durable for the deployed app (e.g. a database or object store), if long-term monitoring becomes a priority.
- [ ] Revisit document filtering for repositories with larger/more complex documentation structures.

## 💬 Status

This is a learning project, built and iterated on as part of hands-on AI engineering practice. Feedback and suggestions are welcome — this is a genuine work in progress rather than a finished product.
2. **Index** — builds a searchable text index over the documents using [minsearch](https://github.com/alexeygrigorev/minsearch).
3. **Search tool** — wraps the index as a callable tool, enriching each result with a direct GitHub citation URL.
4. **Agent** — a [pydantic-ai](https://ai.pydantic.dev/) agent, instructed to always search before answering and to cite every factual claim with a source link.
5. **UI** — a [Streamlit](https://streamlit.io/) chat interface, streaming responses token-by-token as the agent generates them.
6. **Logging** — every interaction is written to a local JSON log for later inspection and debugging.

## Project structure

```
barrier/
├── app.py            # Streamlit UI, chat loop, response streaming
├── ingest.py          # Repo download, document extraction, chunking, indexing
├── search_tools.py    # Search tool wrapper — queries the index, builds citation URLs
├── search_agent.py    # Agent configuration and system prompt
├── logs.py            # Conversation logging to JSON
├── pyproject.toml     # Dependencies (PEP 621 format, managed with uv)
└── README.md
```

## Tech stack

- **LLM orchestration:** [pydantic-ai](https://ai.pydantic.dev/)
- **Search/indexing:** [minsearch](https://github.com/alexeygrigorev/minsearch)
- **Document parsing:** [python-frontmatter](https://python-frontmatter.readthedocs.io/)
- **UI:** [Streamlit](https://streamlit.io/)
- **LLM provider:** OpenAI (`gpt-4o-mini` by default)
- **Dependency management:** [uv](https://docs.astral.sh/uv/), `pyproject.toml`

## Getting started

### Prerequisites

- Python 3.11+
- An OpenAI API key
- [uv](https://docs.astral.sh/uv/) installed

### Setup

1. Clone the repository and navigate into the project folder.

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Create a `.env` file in the project root with your API key:
   ```
   OPENAI_API_KEY=your-key-here
   ```

4. Run the app:
   ```bash
   uv run streamlit run app.py
   ```

The app will be available at `http://localhost:8501`. On first load, it will download and index the target repository — this may take a few seconds.

### Configuration

The target repository is currently set in `app.py`:

```python
REPO_OWNER = "debauchee"
REPO_NAME = "barrier"
```

Change these to point the assistant at a different repository's documentation. Note that if the repository has a very different file structure, you may want to revisit the (currently disabled) document filtering logic in `ingest.py`.

## Deployment

This app is deployed on [Streamlit Community Cloud](https://streamlit.io/cloud). A few environment-specific notes if you're deploying your own copy:

- Streamlit Cloud installs dependencies via Poetry when it detects a `pyproject.toml`. Since this project doesn't need to be installed as a package, `package-mode = false` is set under `[tool.poetry]` to avoid installation errors.
- `st.cache_resource` is used to ensure the (relatively expensive) ingestion and agent setup only runs once per app process, not on every user interaction.
- Logs written by `logs.py` are **not persisted** on Streamlit Cloud — the local filesystem is ephemeral and gets wiped on every restart/redeploy. Logging is primarily useful for local development in its current form.

## Roadmap

- [ ] **Evaluations** — automated eval suite to measure retrieval quality and answer correctness/citation accuracy against a set of reference questions (in progress).
- [ ] Persist logs somewhere durable for the deployed app (e.g. a database or object store), if long-term monitoring becomes a priority.
- [ ] Revisit document filtering for repositories with larger/more complex documentation structures.

## Status

This is a learning project, built and iterated on as part of hands-on AI engineering practice. Feedback and suggestions are welcome — this is a genuine work in progress rather than a finished product.
