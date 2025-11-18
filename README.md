# LLM Aggregator

A comprehensive model aggregator service for discovering, enriching, and cataloging Large Language Models (LLMs) from multiple local backends. Provides a web interface to browse and manage your model collection with detailed metadata.

## Features

- **Multi-Provider Discovery**: Automatically discovers models from multiple LLM servers running on different ports
- **AI-Powered Enrichment**: Uses a configurable "brain" LLM to enrich model metadata with details like model family, context size, quantization, and capabilities
- **Web Catalog Interface**: Clean web UI for browsing your model collection with filtering and sorting
- **Real-time Statistics**: Monitors system resources like RAM usage
- **REST API**: Programmatic access to model data and statistics
- **Background Processing**: Continuous model discovery and enrichment without blocking the UI
- **OpenAI-Compatible**: Works with any LLM server that implements the OpenAI `/v1/models` API

## Installation

### Prerequisites

- Python 3.10 or higher
- One or more running LLM servers (Ollama, llama.cpp, nexa, etc.) with OpenAI-compatible APIs

### Install from Source

```bash
git clone https://github.com/Wuodan/llm-aggregator.git
cd llm-aggregator
pip install -e .
```

### Install from PyPI

```bash
pip install llm-aggregator
```

## Configuration

All runtime behavior is controlled through the YAML file pointed to by the `LLM_AGGREGATOR_CONFIG` environment variable. Use [config.yaml](config.yaml) as a reference template.

### Configuration Options

- **host / port** – Where the FastAPI server and static frontend bind.
- **log_level** – Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Defaults to `INFO` if omitted.
- **brain** – Settings for the enrichment LLM:
  - `base_url` – HTTP endpoint of the enrichment provider.
  - `id` – Model identifier passed to the provider.
  - `api_key` – Optional bearer token injected into requests.
  - `max_batch_size` – Number of models to enrich at once.
- **time** – Background scheduling knobs (all in seconds):
  - `fetch_models_interval`
  - `fetch_models_timeout`
  - `enrich_models_timeout`
  - `enrich_idle_sleep`
- **providers** – Each entry describes an OpenAI-compatible backend to query:
  - `base_url` – Public URL returned via the REST API.
  - `internal_base_url` – Optional internal URL used for server-to-server calls; defaults to `base_url` when omitted.

## Usage

Set the `LLM_AGGREGATOR_CONFIG` environment variable to point at your [config.yaml](config.yaml) and the service will load it on startup.

### Starting the Service

```bash
export LLM_AGGREGATOR_CONFIG=/path/to/config.yaml
llm-aggregator
```

Or run directly:

```bash
export LLM_AGGREGATOR_CONFIG=/path/to/config.yaml
python -m llm_aggregator
```

The web interface will be available at `http://localhost:8888`

### Web Interface

The web catalog displays:
- **Model**: Model identifier
- **Port**: Provider port
- **Types**: Model capabilities (llm, vlm, embedder, etc.)
- **Family**: Model architecture family
- **Context**: Context window size
- **Quant**: Quantization level
- **Param**: Parameter count
- **Summary**: Brief model description
