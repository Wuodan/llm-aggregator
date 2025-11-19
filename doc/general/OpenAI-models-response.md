# `/v1/models` Response Shape

This describes the expected payload when issuing a `GET` request to the OpenAI-compatible endpoint `/v1/models`, based
on the official OpenAPI specification published by
OpenAI ([source](https://app.stainless.com/api/spec/documented/openai/openapi.documented.yml)).

## Request Overview

- **HTTP method:** `GET`
- **URL:** `https://api.openai.com/v1/models` (replace host for compatible servers)
- **Auth:** `Authorization: Bearer <API key>`
- **Content-Type:** no body required

## Successful Response (`200 OK`)

The response is a JSON object conforming to the `ListModelsResponse` schema.

> **Sample payload** from the spec:
>
> ```json
> {
>   "object": "list",
>   "data": [
>     {
>       "id": "model-id-0",
>       "object": "model",
>       "created": 1686935002,
>       "owned_by": "organization-owner"
>     },
>     {
>       "id": "model-id-1",
>       "object": "model",
>       "created": 1686935002,
>       "owned_by": "organization-owner"
>     },
>     {
>       "id": "model-id-2",
>       "object": "model",
>       "created": 1686935002,
>       "owned_by": "openai"
>     }
>   ]
> }
> ```

### Top-Level Fields

| Field    | Type                     | Description                                                    |
|----------|--------------------------|----------------------------------------------------------------|
| `object` | string (const: `"list"`) | Identifies this payload as a list wrapper.                     |
| `data`   | array of `Model` objects | Each entry describes a single model available through the API. |

**Required vs. optional:** both `object` and `data` are mandatory according to the `ListModelsResponse` schema; there
are no optional top-level fields in the spec for this
response ([source](https://app.stainless.com/api/spec/documented/openai/openapi.documented.yml)).

### `Model` Object Schema

Every entry inside `data` has the following fields:

| Field      | Type                      | Description                                              |
|------------|---------------------------|----------------------------------------------------------|
| `id`       | string                    | Model identifier you pass when invoking other endpoints. |
| `object`   | string (const: `"model"`) | Type marker for SDKs and tooling.                        |
| `created`  | integer                   | Unix timestamp (seconds) when the model was registered.  |
| `owned_by` | string                    | Organization or provider that owns the model.            |

**Required vs. optional:** the spec lists `id`, `object`, `created`, and `owned_by` as required. There are no optional
fields on the `Model` object—the schema intentionally keeps it minimal for
compatibility ([source](https://app.stainless.com/api/spec/documented/openai/openapi.documented.yml)).

Use this structure when implementing or validating OpenAI-compatible servers so official SDKs can enumerate models
without custom handling.

## Llama.cpp `meta` Extension

The upstream spec does **not** mention any additional properties on the `Model` object, but llama.cpp extends the
response with a `meta` object that surfaces GGUF metadata ([source](llama.cpp/tools/server/README.md#L1151)).

- `meta` is optional and can be `null` (for example, while the model is still loading).
- When present it is a dictionary of key/value pairs describing the loaded model—typical keys include `vocab_type`,
  `n_vocab`, `n_ctx_train`, `n_embd`, `n_params`, and `size`.
- Example straight from the llama.cpp server documentation:

  ```json
  {
      "object": "list",
      "data": [
          {
              "id": "../models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
              "object": "model",
              "created": 1735142223,
              "owned_by": "llamacpp",
              "meta": {
                  "vocab_type": 2,
                  "n_vocab": 128256,
                  "n_ctx_train": 131072,
                  "n_embd": 4096,
                  "n_params": 8030261312,
                  "size": 4912898304
              }
          }
      ]
  }
  ```

Because `meta` is non-standard, clients that require strict OpenAI compatibility should ignore unknown fields, while
llama.cpp-specific tooling can leverage these diagnostics. Your own server can follow the same pattern if you want to
expose GGUF metadata alongside the canonical `id` / `object` / `created` / `owned_by` fields.
