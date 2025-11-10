# Package Layout for llm-aggregator

```
model_aggregator/
├── __init__.py
├── __main__.py
├── main.py              # app factory + uvicorn entry
├── config.py            # loads typed settings from config.yaml
├── config.yaml          # runtime config (new)
├── models.py            # dataclasses: ProviderConfig, ModelKey, ModelInfo, EnrichedModel
├── services/
│   ├── __init__.py
│   ├── model_sources.py   # fetch /v1/models from all providers
│   ├── model_store.py     # in-memory state + queue
│   ├── brain_client.py    # call enrichment LLM (refactor of current brain_client)
│   └── tasks.py           # background loops for refresh + enrichment
├── api.py               # /api/models -> reads from model_store only
└── static/
    └── index.html
```