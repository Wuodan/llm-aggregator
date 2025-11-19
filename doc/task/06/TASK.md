# Task 06: Config-Driven Model Info Sources

## Goal
Move the hard-coded website definitions (HuggingFace + Ollama) into the YAML configuration so users can add, remove, or reorder sources without modifying code.

## Requirements
1. **New configuration structure**
   - Introduce a list (e.g., `model_info_sources`) in `config.yaml`.
   - Each entry must declare at least:
     - `name` (human-readable label shown in enrichment prompts, e.g., `"HuggingFace.co"`).
     - `url_template` (string containing `{model_id}` where the normalized id should be injected).
   - Additional optional fields (like a unique `key` for caching) may be supported, but `name` and `url_template` are mandatory.
   - Provide defaults for HuggingFace and Ollama via the sample config so existing behavior remains unchanged until a user edits the list.

2. **Runtime enforcement**
   - Replace the static `WebsiteSource` constants in `services/model_info/_sources.py` with instances built from the config data.
   - If a config entry is invalid (missing required fields, missing `{model_id}`, empty string, duplicate key, etc.), fail fast during startup by raising an error—do not silently log and continue.
   - Ensure cache keys remain stable: either require a `key` field or derive one deterministically from the name (e.g., slugify the label).

3. **Prompt + fetch plumbing**
   - All downstream consumers (`fetch_model_markdown`, enrichment prompt prefixes, etc.) must pull provider labels and URL templates from the new config-derived objects.
   - No hard-coded provider names may remain in enrichment prompts or user messages.

4. **Documentation**
   - Update `config.yaml` (and README if needed) to document the new `model_info_sources` block, including an example that matches the previous defaults.
   - Clarify that `{model_id}` is required inside every template and describe what happens when the field is omitted (startup error).

5. **Tests**
   - Extend or add tests covering:
     - Successful loading of multiple sources from config.
     - Error handling when `url_template` lacks `{model_id}` or required fields are missing.
     - Integration of labels into enrichment prompts/messages.
