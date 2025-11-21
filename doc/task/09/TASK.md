# Task 09: Gather model files size

Per model, I want to add the total file size on disk of the model to the output information.

Each provider (Ollama, nexa, llama.cpp, etc.) handles the files differently,
see [get-mode-files-size.md](get-mode-files-size.md).

So I need a kind of plugin system to implement the file size gathering for each provider.

So the config of each provider will get a new option structure `files_size_gatherer` with these fields:

- type: type of gatherer
  - for type `custom` we also need a `path to script or executable`
- base path/url for execution: root path of where the provider stores the model files
- optional additional arguments (at least for custom type)

Looking at how simple the llama.cpp and nexa.ai gatherers are in bash

pseudo-description of bash gatherer for llama.cpp and nexa:
- root-path plus model-name with `/` and `:` replaced by wildcard and quant removed plus postfix "*" gives all files
- simply sum up file sizes

And that the gatherer for Ollama could also be easily written in bash, I consider using only type `custom` and providing 2-3 scripts for my current providers. What do you think?

## Changes

### REST endpoint

My apps REST endpoint `GET /v1/models` shall have a new field in the `llm_aggregator` object: `files_size`

### Config

Additional optional structure `files_size_gatherer` as described above.