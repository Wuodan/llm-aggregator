# Subtask 07-02: Configurable + Optional UI

## Objectives
Let operators control how (or if) the UI is served by introducing a dedicated config block.

## Requirements
1. **Config surface**
   - Add a `ui` (name flexible but singular) section to `config.yaml` with at least:
     - `builtin_enabled` (bool, default `true`): when `false`, the service must not mount `/` or `/static`; only REST endpoints remain available.
     - `builtin_static_path` (string, defaulting to the package’s `static/` folder): used when `builtin_enabled` is `true` and no custom UI is supplied.
     - `custom_static_path` (optional string): when set, serve static files (and the `index.html`) from this location instead of the bundled assets.
   - Validation: fail startup if any referenced directory/file path is missing or unreadable.

2. **Serving behavior**
   - When `builtin_enabled` is `true` and `custom_static_path` is unset: serve the current UI exactly as today, including cache-busting query params for `/static/main.js`.
   - When `custom_static_path` is set:
     - Serve `/` and `/static` from that folder (honoring the no-cache headers we already use).
     - You may reuse the same simple cache-busting approach used for the builtin UI (e.g., appending `?v=<version>`). No extra plug-in or user-defined logic is required; if the shared mechanism is awkward, it is acceptable to skip cache-busting for custom paths.
   - When `builtin_enabled` is `false`: neither `/` nor `/static` should resolve; FastAPI should only expose the REST endpoints (e.g., `/v1/models`, `/api/stats`, `/api/clear`).

3. **Documentation**
   - Update `config.yaml` comments and README to describe the `ui` block, examples for:
     - default bundled UI
     - pointing at a custom directory
     - disabling UI entirely
   - Mention the cache-busting rule difference between bundled vs. custom UI.

4. **Tests**
   - Cover each mode (builtin, custom, disabled) to ensure routes and static files behave as expected.
   - Include regression tests to verify cache-busting is skipped for custom UI paths.

## Out of Scope
- Any redesign of the HTML/JS content itself.
- Alternative HTTP servers or middleware unrelated to static file serving.
