# Task 05: OpenAI-Compatible `/v1/models`

## Goal
Expose the OpenAI ListModelsResponse at `/v1/models` and remove the legacy `/api/models` endpoint. The response must be consumable by any OpenAI-compatible client while still surfacing the aggregator-specific metadata that already powers the UI.

## Background
- Current code serves a custom snapshot at `/api/models`.
- `doc/general/OpenAI-models-response.md` documents the official schema (`object=list`, `data=[Model]`, etc.).
- Downstream tooling (including the UI) relies on the extra metadata currently emitted in `ModelStore.get_snapshot()`.

## Requirements
1. **Endpoint replacement**
   - Implement `GET /v1/models` returning JSON that matches the OpenAI ListModelsResponse schema:
     - Top level: `{"object": "list", "data": [...]}`.
     - Every entry uses `object: "model"` and includes the canonical OpenAI fields (`id`, `created`, `owned_by`, `permission`, etc.) exactly as provided by each upstream server, without stripping unknown/custom properties.
   - Delete `/api/models`; no compatibility shim is required.

2. **Retain provider payloads**
   - When consolidating provider responses, preserve every key that the upstream `/v1/models` entries expose. The only field that the aggregator needs to supply itself is the `id` string (in case a backend omits or alters it).
   - If a provider extends the schema (e.g., llama.cpp’s `meta`), those properties must remain in our `data` entry verbatim.

3. **`llm-aggregator` augmentation**
   - Each `Model` object must add a sibling object named `llm-aggregator`.
   - That object contains exactly the data points we used to emit previously on `/api/models`, minus the duplicated `id`. Today that includes (but is not limited to):
     - `base_url` (public provider URL)
     - any enrichment output such as `summary`, `types`, `model_family`, `context_size`, `quant`, `param`
     - any future aggregator-only attributes produced by enrichment or local bookkeeping
   - Do **not** mirror this data back into the top-level OpenAI fields. Everything aggregator-specific belongs inside `llm-aggregator`.

4. **Sorting and ordering**
   - Preserve a deterministic ordering of the returned models (same order we use today: by provider base URL, then case-insensitive model id), so downstream consumers and snapshots remain predictable.

5. **Validation and tests**
   - Update/extend automated tests to assert that:
     - `/v1/models` returns the required OpenAI shape.
     - Provider metadata (e.g., `meta`) is untouched.
     - The `llm-aggregator` object contains the prior custom fields and omits `id`.
   - Remove tests targeting `/api/models`.

6. **Documentation**
   - Reference `doc/general/OpenAI-models-response.md` where appropriate (e.g., in code comments or dev notes).

## Out of Scope
- UI changes (`index.html`, `static/main.js`) are explicitly handled later; do not update them here.
- No behavioral changes for `/api/stats` or `/api/clear`.
