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

The service is configured via `config.yaml` in the project root. 

### Configuration Options

- **host/port**: Server binding address
- **brain**: Configuration for the enrichment LLM
  - `host`: Base URL of the enrichment model server
  - `port`: Port where enrichment model runs
  - `id`: Model identifier for enrichment
  - `api_key`: Optional API key for authentication
  - `max_batch_size`: Models to enrich per batch
- **time**: Timing configurations for background tasks
- **providers**: List of LLM servers to monitor
  - `base_url`: Base endpoint for the provider
  - `port`: Port number for model discovery

## Usage

### Starting the Service

```bash
llm-aggregator
```

Or run directly:

```bash
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