# Task 08: README Refresh

## Goal
Rewrite the README so it clearly explains, to a technical audience, what the project does, how the REST API works, and how to replace the integrated UI.

## Requirements
1. **Plain-language feature overview**
   - Replace the current “Features” list with a concise explanation of the project’s purpose and user-facing benefits.
   - Emphasize:
     - Aggregating models from multiple OpenAI-compatible servers.
     - The enrichment step that uses model ids plus website context (HuggingFace, Ollama, etc.) to produce metadata for the table.
     - The integrated table UI and RAM widget.
     - The availability of REST endpoints (model list, stats, clear) that can power other tools.
   - Keep the tone technical and matter-of-fact—no marketing fluff or buzzwords.

2. **REST API section**
   - Document each endpoint with HTTP method, path, brief description, and the essential request/response structure:
     - `GET /v1/models`
     - `GET /api/stats`
     - `POST /api/clear`
   - Mention authentication expectations (if any) and note that `/v1/models` follows the OpenAI schema plus the `llm-aggregator` extension from Task 05.

3. **UI replacement instructions**
   - Based on the configuration work from Task 07, explain how to:
     - Use the bundled UI (default).
     - Point the app at a custom static directory.
     - Disable the UI entirely and rely solely on the REST API.
   - Highlight the cache-busting rule difference (built-in UI adds `?v=<version>`; custom paths do not).

4. **General cleanup**
   - Ensure references to configuration fields (including the new `model_info_sources` and `ui` blocks) are up to date.
   - Keep the rest of the README structure intact unless edits are needed to support the new sections.

## Out of Scope
- Implementation work for the UI or API—this task only touches documentation.
- Deep tutorials; keep explanations focused on what the app does and how to configure/use it.
