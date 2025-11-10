# llm-aggregator Architecture

The project `llm-aggregator` already has a working PoC. Now it's time to think about an extendable modular architecture.

This is written by an Java developer who is entirely class driven. In Python the best practices are different but the logical separation shall remain.
And having small parts and small files in logical units is clean code standard.
So the below shall be transfered to Pythons best-practice with that in mind.

## Data objects

### Data objects: Model object
When I speak of a model below, I always mean an object holding {url, port, model-name} together.

### Data objects: ModelDetail object
This currently holds modelsSummary and modelTypes but might grow by size of foles on disk, etc.

### Data objects: Provider object
This should be loaded from a config file which is a param to application
This currenlty holds:
- url: http://10.7.2.100:<PORT>
- auth_method: "" or "model=api-key"

## Service files/classes

### Main class/file:
Very slim, just starts other classes/files/objects.
But nothing is blocking at the start!
The construtors of objects are executed and then the app is repsonding.
Any loading of data happens non-blocking in the background.

### ModelService:
Responsible for holding and managing the cached set of models.
That cached set is empty at start and can immediatly be read from a getter (or set is somehow public, it's python).

It has a cron-job to periodically pull current set from the /v1/models of Provider objects (file read each time would auto-load updates to the file).
When a current set is collected, this class/file does these things:
- update cached set
- it passes old and new set of models to ModelDetailService (see below), lets say to a method `updateModels`

### ModelDetailService
Similar to ModelService this holds a cache: a cached map of key=Model and values=ModelDetails
Again: This cache object is empty at start, immediatly accessible.

It also has a queue of models to update.

When it receives an update of old/new models from ModelService, then it creates a delta from old and new cached set: additions and subtractions.
- subtractions: are removed from the cached map AND the queue
- additions are added to the queue (unique models in the queue)

Somewhere there must be a runner, either in ModelDetailService or as separate service.
This runner 'watches' the queue of ModelDetailService, when the queue has items the runner processes them in batches (batch size configurable, config file seupt wanted)
Each batch of models is handed to ModelDetailLoaderService - async, non blocking, fire and forget!

### ModelDetailLoaderService
Receives a batch of models, researches information about them:
- currently there is only the call to the LLM to get a JSON with information. This is also the reason for batching, it works for 15 items but 20+ run into timeouts.
- this MUST be a separate service or such as this is very likely to be extended (file sizes of models, HF-website reading, etc).
When information is found, it is handed to ModelDetailService to update the map. Here a 'merge' strategy for the ModelDetail object values of the map should be used.

### ApiService
The REST endpoint service.
Does minimal logic on a REST request:
- get set of Models from ModelService (from its cache)
- get ModelDetail map from ModelDetailService
- construct output json