# Model File Size Gathering

Each provider can declare an optional `files_size_gatherer` block to expose an on-disk
size for its models. The block lives under a provider entry in `config.yaml` and
supports these fields:

- `path`: required; absolute or relative path to an executable/script
- `base_path`: filesystem root or base URL passed to the script
- `timeout_seconds`: optional per-gatherer timeout (defaults to 15s)

Example:

```yaml
providers:
  - base_url: https://ollama.example/v1
    files_size_gatherer:
      base_path: /var/lib/ollama/models
      # Packaged script (resolved automatically when relative):
      path: files-size-ollama.sh
      timeout_seconds: 15
  - base_url: https://custom.example/v1
    files_size_gatherer:
      base_path: /mnt/models
      path: /path/to/my/custom-script.sh
```

Behavior:

- The script is invoked as `<path> <base_path> <full_model_name>`.
- It must print the total size in bytes to stdout.

Bundled scripts for common providers are installed with the package at
`<site-packages>/llm_aggregator/scripts/` and can be referenced by
relative name in config:
- `files-size-ollama.sh`
- `files-size-llama-cpp.sh`
- `files-size-nexa.sh`

You can discover the absolute path at runtime:

```bash
python - <<'PY'
import llm_aggregator, pathlib
root = pathlib.Path(llm_aggregator.__file__).parent / "scripts"
print(root / "files-size-ollama.sh")
PY
```

The new field is attached to enrichment metadata and exported as
`meta.size` (bytes) in `/v1/models`. If gathering is disabled or
fails, the field is omitted/null without failing the endpoint.

See `doc/task/09/get-mode-files-size.md` for manual examples of locating provider
files.
