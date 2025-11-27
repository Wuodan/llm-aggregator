from __future__ import annotations

import asyncio

from llm_aggregator.models import (
    FilesSizeGathererConfig,
    ProviderConfig,
    make_model,
)
from llm_aggregator.services.files_size import gather_files_size


def _model(model_id: str, cfg: FilesSizeGathererConfig):
    provider_name = "provider"
    provider = ProviderConfig(
        base_url="https://provider.example/v1",
        internal_base_url="http://provider.local/v1",
        files_size_gatherer=cfg,
    )
    model = make_model(provider_name, provider, {"id": model_id})
    # Ensure global settings include this provider for gatherer lookup
    import llm_aggregator.config as config_module
    settings = config_module.get_settings()
    if provider_name not in settings.providers:
        settings.providers[provider_name] = provider
    return model


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


def test_gatherer_returns_none_when_disabled():
    provider = ProviderConfig(
        base_url="https://provider.example/v1",
        internal_base_url="http://provider.local/v1",
        files_size_gatherer=None,
    )
    model = make_model("provider", provider, {"id": "any"})
    assert asyncio.run(gather_files_size(model)) is None


def test_gatherer_returns_none_when_path_missing(tmp_path):
    cfg = FilesSizeGathererConfig(
        base_path=str(tmp_path),
        path=str(tmp_path / "missing.sh"),
        timeout_seconds=1,
    )
    model = _model("any/model", cfg)
    assert asyncio.run(gather_files_size(model)) is None


def test_gatherer_handles_nonzero_exit(tmp_path):
    script = tmp_path / "exit_1.sh"
    script.write_text("#!/usr/bin/env bash\necho nope >&2\nexit 1\n", encoding="utf-8")
    script.chmod(0o755)

    cfg = FilesSizeGathererConfig(
        base_path=str(tmp_path),
        path=str(script),
        timeout_seconds=1,
    )
    model = _model("any/model", cfg)
    assert asyncio.run(gather_files_size(model)) is None


def test_gatherer_handles_non_integer_output(tmp_path):
    script = tmp_path / "print_text.sh"
    script.write_text("#!/usr/bin/env bash\necho not-a-number\n", encoding="utf-8")
    script.chmod(0o755)

    cfg = FilesSizeGathererConfig(
        base_path=str(tmp_path),
        path=str(script),
        timeout_seconds=1,
    )
    model = _model("any/model", cfg)
    assert asyncio.run(gather_files_size(model)) is None


def test_gatherer_handles_negative_output(tmp_path):
    script = tmp_path / "print_negative.sh"
    script.write_text("#!/usr/bin/env bash\necho -42\n", encoding="utf-8")
    script.chmod(0o755)

    cfg = FilesSizeGathererConfig(
        base_path=str(tmp_path),
        path=str(script),
        timeout_seconds=1,
    )
    model = _model("any/model", cfg)
    assert asyncio.run(gather_files_size(model)) is None


def test_gatherer_times_out(tmp_path):
    script = tmp_path / "sleep.sh"
    script.write_text("#!/usr/bin/env bash\nsleep 2\n", encoding="utf-8")
    script.chmod(0o755)

    cfg = FilesSizeGathererConfig(
        base_path=str(tmp_path),
        path=str(script),
        timeout_seconds=0.1,
    )
    model = _model("any/model", cfg)
    assert asyncio.run(gather_files_size(model)) is None
