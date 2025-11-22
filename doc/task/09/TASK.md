# Task 09: Model File Size Gathering

## Goal
Annotate each model with its total on-disk size (bytes) via a per-provider gatherer, and expose that value to enrichment logic and `/v1/models`.

## Background
- Providers store files differently; see `doc/task/09/get-mode-files-size.md` for manual examples (nexa.ai, llama.cpp, Ollama).
- The app tracks ~50 models, so file-size collection must *not* run during `/v1/models`. It may run per-model during the existing enrichment step (alongside website-to-markdown fetches) and can block that step; parallelizing the fetches is fine.

## Requirements
1. **Config shape**
   - Add an optional `files_size_gatherer` block to each provider config.
   - Fields:
     - `type`: enum of supported gatherers (`ollama`, `llama_cpp`, `nexa`, `custom`).
     - `base_path` (or base URL): root where the provider stores model files.
     - `path` (custom only): path to the script or executable.
     - `args` (optional): extra arguments appended after the model name.
   - Document the custom invocation contract: `<path> <base_path> <full_model_name> [arg1 ...]`; the script prints the size in bytes to stdout.

2. **Gathering behavior**
   - Trigger file-size collection during per-model enrichment, never on the `/v1/models` list call.
   - Run both website-to-markdown and file-size gathering in parallel for each model (fix the current non-parallel website call). Failures must not break model processing (log and return null/omit).
   - Treat the size as an integer number of bytes.

3. **Provider implementations**
   - Built-in gatherers for `llama_cpp` and `nexa` should follow the wildcard strategy described in `get-mode-files-size.md` (replace `/` and `:` in model id with path-friendly wildcards, drop quant suffix where noted, glob with `*`, sum file sizes under `base_path`).
   - Built-in gatherer for `ollama` should read the manifest under `base_path` and sum the `layers[*].size` values (see the doc for layout hints).
   - The `custom` gatherer executes the configured script; ensure execution is sandboxed/safe and has timeouts/logging.

4. **Data surfaces**
   - Store the size on the model metadata (e.g., inside its `meta` data) so it can be sent to the “brain” LLM if needed.
   - Add `meta.size` to each entry in `GET /v1/models`, expressed in bytes.
   - If gathering is disabled or fails, omit or null the field without failing the endpoint.

5. **Validation and docs**
   - Tests: config parsing/validation, gatherer dispatch (including a stubbed custom script), error handling, and `/v1/models` responding with the new field when present.
   - Add developer notes describing the config block, gatherer types, and pointers to `doc/task/09/get-mode-files-size.md`.

## Out of Scope
- UI/table changes; this is backend metadata only.
- Time-consuming global scans during `/v1/models`; all gathering stays per-model at enrichment time.
