from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebsiteSource:
    key: str
    provider_label: str
    url_template: str

    def build_url(self, model_id: str) -> str:
        return self.url_template.format(model_id=model_id)


HUGGING_FACE = WebsiteSource(
    key="huggingface",
    provider_label="HuggingFace.co",
    url_template="https://huggingface.co/{model_id}",
)

OLLAMA = WebsiteSource(
    key="ollama",
    provider_label="Ollama.com",
    url_template="https://ollama.com/library/{model_id}",
)

ALL_SOURCES = (HUGGING_FACE, OLLAMA)
