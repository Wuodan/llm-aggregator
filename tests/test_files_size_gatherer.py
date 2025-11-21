from __future__ import annotations

import asyncio

from llm_aggregator.models import (
    FilesSizeGathererConfig,
    ProviderConfig,
    make_model,
)
from llm_aggregator.services.files_size import gather_files_size


def _model(model_id: str, cfg: FilesSizeGathererConfig):
    provider = ProviderConfig(
        base_url="https://provider.example/v1",
        internal_base_url="http://provider.local/v1",
        files_size_gatherer=cfg,
    )
    return make_model(provider, {"id": model_id})


def test_custom_gatherer_executes_script(tmp_path):
    script = tmp_path / "print_size.sh"
    script.write_text("#!/usr/bin/env bash\nprintf 123\n", encoding="utf-8")
    script.chmod(0o755)

    cfg = FilesSizeGathererConfig(
        base_path="/does/not/matter",
        path=str(script),
        timeout_seconds=1,
    )
    model = _model("any/model", cfg)
    size = asyncio.run(gather_files_size(model))
    assert size == 123
