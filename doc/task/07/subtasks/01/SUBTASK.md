# Subtask 07-01: Serve Index Without Fragile Replacements

## Objectives
1. Remove the string-based `html.replace` hacks in `src/llm_aggregator/api.py`.
2. Decide what to do with the `api_base_url` override: either eliminate the concept entirely (preferred unless there is a compelling use-case) or document and test it properly.
3. Keep cache-busting for the bundled `main.js` when serving the built-in UI from our package data.

## Requirements
- The `/` handler must render `index.html` without searching/replacing literal substrings. Use whichever approach is most maintainable (templating, placeholder tokens, etc.), but the result must be deterministic and covered by tests.
- If `api_base_url` is removed:
  - purge the attribute from settings, tests, and docs;
  - derive the API base solely from the incoming request.
- If `api_base_url` stays:
  - document what it controls and why it is useful;
  - ensure tests cover both configured and request-derived behavior.
- Cache busting of `/static/main.js` for the bundled UI should still append `?v=<settings.version>` (or equivalent) when we serve our own assets.
- Update/extend tests to assert the new rendering approach and `api_base` behavior.

## Out of Scope
- Configurable/static UI paths (handled in Subtask 07-02).
- Any changes to the actual HTML or JS content.
