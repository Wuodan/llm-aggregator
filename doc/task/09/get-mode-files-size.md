# How-To Read Model File Sizes from LLM Servers

This describes how to manually find the relevant files per model on the disk and shows an examples of file size
summarization.

## Nexa.ai

Given full model name (with optional quant): `NexaAI/gemma-3-4b-it-8bit-MLX:8BIT`

I manually find these files:

```
% du -hsc /Volumes/OWCUltra/nexa.ai/nexa_sdk/models/NexaAI/gemma-3-4b-it-8bit-MLX*
5.3G    /Volumes/OWCUltra/nexa.ai/nexa_sdk/models/NexaAI/gemma-3-4b-it-8bit-MLX
  0B    /Volumes/OWCUltra/nexa.ai/nexa_sdk/models/NexaAI/gemma-3-4b-it-8bit-MLX.lock
5.3G    total
```

## llama.cpp

Given full model name (with optional quant): `unsloth/GLM-4.6-GGUF:UD-IQ2_XXS`

I manually find these files:

```
% du -hsc /Volumes/OWCUltra/llama_cpp/llama-cache/unsloth?GLM-4.6-GGUF?UD-IQ2_XXS*
 46G    /Volumes/OWCUltra/llama_cpp/llama-cache/unsloth_GLM-4.6-GGUF_UD-IQ2_XXS_GLM-4.6-UD-IQ2_XXS-00001-of-00003.gguf
4.0K    /Volumes/OWCUltra/llama_cpp/llama-cache/unsloth_GLM-4.6-GGUF_UD-IQ2_XXS_GLM-4.6-UD-IQ2_XXS-00001-of-00003.gguf.etag
 47G    /Volumes/OWCUltra/llama_cpp/llama-cache/unsloth_GLM-4.6-GGUF_UD-IQ2_XXS_GLM-4.6-UD-IQ2_XXS-00002-of-00003.gguf
4.0K    /Volumes/OWCUltra/llama_cpp/llama-cache/unsloth_GLM-4.6-GGUF_UD-IQ2_XXS_GLM-4.6-UD-IQ2_XXS-00002-of-00003.gguf.etag
 15G    /Volumes/OWCUltra/llama_cpp/llama-cache/unsloth_GLM-4.6-GGUF_UD-IQ2_XXS_GLM-4.6-UD-IQ2_XXS-00003-of-00003.gguf
4.0K    /Volumes/OWCUltra/llama_cpp/llama-cache/unsloth_GLM-4.6-GGUF_UD-IQ2_XXS_GLM-4.6-UD-IQ2_XXS-00003-of-00003.gguf.etag
107G    total
```

## Ollama

Given full model name (with optional quant): `deepseek-r1:14b-qwen-distill-q8_0`

With Ollama we have to find the model information from a `manifest` file, only "layers" matter here for files.

```
% cat models/manifests/registry.ollama.ai/library/deepseek-r1/14b-qwen-distill-q8_0 | jq      
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
  "config": {
    "mediaType": "application/vnd.docker.container.image.v1+json",
    "digest": "sha256:4404ac8504610f3177e8c3291d853f36e06cc0afff8ea0b072b49a9914e87901",
    "size": 486
  },
  "layers": [
    {
      "mediaType": "application/vnd.ollama.image.model",
      "digest": "sha256:1604e71f507e1a0597896f2a8dda3b8acb574d8559526bb9adad961386543649",
      "size": 15701597312
    },
    {
      "mediaType": "application/vnd.ollama.image.template",
      "digest": "sha256:c5ad996bda6eed4df6e3b605a9869647624851ac248209d22fd5e2c0cc1121d3",
      "size": 556
    },
    {
      "mediaType": "application/vnd.ollama.image.license",
      "digest": "sha256:6e4c38e1172f42fdbff13edf9a7a017679fb82b0fde415a3e8b3c31c6ed4a4e4",
      "size": 1065
    },
    {
      "mediaType": "application/vnd.ollama.image.params",
      "digest": "sha256:f4d24e9138dd4603380add165d2b0d970bef471fac194b436ebd50e6147c6588",
      "size": 148
    }
  ]
}
```

The easiest way to get file-size is directly from that manifest file.

For the record, the sha256 hashes represent the real filenames:

```
% du -hsc models/blobs/sha256-1604e71f507e1a0597896f2a8dda3b8acb574d8559526bb9adad961386543649                  
 15G    models/blobs/sha256-1604e71f507e1a0597896f2a8dda3b8acb574d8559526bb9adad961386543649
 15G    total
```

## Custom script/executable call

Next to the 3 methods above (or 2 if one combines nexa and llama.cpp), I want a custom method that allows to specify:

- path to script or executable
- base path/url for execution
- optional additional arguments

The script/executable will then by my code be called as in:

```bash
<path to script or executable> \
  <base path/url> \
  <full model name> \
  <additional optional argument 1> \
  <additional optional argument 2>
```

The script shall print the file size in bytes to stdout.

## Helper scripts

This repository includes ready-made helpers under `scripts/` (packaged to
`<site-packages>/llm_aggregator/scripts/` when installed):
- `files-size-ollama.sh`
- `files-size-llama-cpp.sh`
- `files-size-nexa.sh`

Each script accepts `<base_path> <full_model_name>` and prints the total size in bytes.
