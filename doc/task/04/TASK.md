# Task 04: Write several task specifications

I have a few tasks in my head, each worthy of its own AI coding session.  
Your task is to refine them in discussion with me and produce a TASK.md in `doc/task/0X/TASK.md` where `X` is a number
starting with 5 (3 tasks were i the past, this is task 04).

Feel free to ask me questions throughout the process, it is important that we get those foundation documents right.

I suggest you read the tasks below, ask me general questions, then we iterate over the tasks one by one.

Also feel free to split tasks into sub-tasks if appropriate, especially those tasks with subsections. Then subtasks
shall be documented in `doc/task/0X/subtasks/0Y/SUBTASK.md`

Important:

- Describe the tasks, not your idea of the solution.
- Remember that each task will be executed in new sessions without memory of our discussion here. Keep the task files
  clean of feedback to me or the details of our discussion here. Only store information relevant to the task execution
  session.

## Task 05: OpenAI compatible /v1/models output

For this task I added a document about the OpenAI compatible response format of /v1/models in
`doc/general/OpenAI-models-response.md`.

I basically want to change the custom response format of current /api/models to the OpenAI compatible format and serve it
under /v1/models. /api/models can then be removed.

### Retail full information from LLM servers

Right now we only return the model-id and base_url in the /v1/models response.  
I want to retain the full information from the LLM servers and include that in our own response to /v1/models.  
Keep this simple, the only field you must hard-code is the "id" field. When this is dynamic, then also the custom "meta"
object form llama.cpp and any other custom fields are automatically included in our response.

### Custom field "llm_aggregator" in response

Like llama.cpp adds its own custom "meta" object, our endpoint shall add a custom "llm_aggregator" object to the response.  
This object shall include all the fields that we currently output except for "id" which is already part of the OpenAI response.

### Ignore UI index.html and main.js

Changing and testing of those 2 files is not part of the task. I will do it myself.

## Task 06: Dynamic sources for html-markdown model info from config

Right now they are hardcoded: HuggingFace.co and Ollama.com  
I want that to be a list in the config like

```
model-info-pages:
  - url: ollama.com/foo
    name: Ollama.com
```

this also means the prefixes to the user message to brain can no longer be hardcoded, all necessary parts must come
from the config (name, etc.).

## Task 07: Custom UI

### Clean up `html.replace` in `api.py`

I think `api_base` is not needed or explain use-case where it's useful.
`api_base` is not used in config nor documented.

And atm we replace text in the static html.  
Would it be easier to just serve the static html on a dynamic path like `index.html?version=$version` instead?

### Let users add custom UI

I want users to be able to add their own UI.
Quick ideas for this:

- config: add path for custom folder to serve static content from other paths on the OS
- config: add boolean flag to serve no static content at all (might not be needed if we can put current static
  content path in config)
- When the app serves no static UI, the user can easily use the REST endpoints to load data into his own frontend

## Task 08: README Update

This is the last task.

### General project info

Instead of the advertisement slang in `## Features` which even I hardly understand, document what the project does with
focus on user benefit and key features
The table in the UI is very important, it's already in the readme. other key benefits/features are:

- combines model info of several OpenAi compatible LLM servers
- Enriches the model info with an LLM (brain) based on:
  - model-id
  - Website information from HuggingFace.co, Ollama.com, etc.
    to produce additional output for Web UIs like the table in the integrated UI
- has integrated simple Web UI
- has additional REST endpoint and output in integrated UI for RAM-Information of app host (must not be equals to LLM
  servers)

### Document REST endpoints

Document the apps REST endpoints

### Document how users can replace the integrated UI
