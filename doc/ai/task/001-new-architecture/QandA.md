1. Providers:
   there are several and the PoC already handles it. url+port nicely defines a provider as we only support OpenAI protocol by /v1
2. Config
   env-vars is to simple, yaml, toml, jwon, your pick
   answer to your questions about values are yes. when we do config-file, we want no hard-coded values in code.
3. Persistence: No Persistence, all in memory.
4. LLM for enrichment: yes, one fixed url, port and it must support /v1/chat/completions
5. Concurrency model
   async were needed only please. And asyncio.Queue unless that makes it all complicated
6. One endpoint: @app.get("/api/models")
7. Provider down: Delete associated models from cache. Log ERROR! No block or extra handling, the next iteration will fix it.