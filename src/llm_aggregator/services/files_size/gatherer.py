from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from llm_aggregator.models import Model
from llm_aggregator.config import get_settings

FILES_SIZE_FIELD = "size"
DEFAULT_TIMEOUT_SECONDS = 15


async def gather_files_size(model: Model) -> int | None:
    """Return total size in bytes for the given model, or None on failure/disable."""
    settings = get_settings()
    provider_cfg = settings.providers.get(model.provider_name)
    if provider_cfg is None:
        return None

    cfg = provider_cfg.files_size_gatherer
    if not cfg:
        return None

    try:
        logging.info("Gathering files size for %s models", model.key.id)

        timeout = cfg.timeout_seconds or DEFAULT_TIMEOUT_SECONDS
        script_path = Path(cfg.path)
        if not script_path.exists():
            logging.error("Custom files_size_gatherer path not found: %s", script_path)
            return None
        cmd = [str(script_path), cfg.base_path, model.key.id]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            logging.error("Custom files_size_gatherer path not found: %s", cfg.path)
            return None
        except Exception as exc:
            logging.error("Failed to start custom files_size_gatherer %s: %r", cfg.path, exc)
            return None

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            logging.error("Custom files_size_gatherer timed out after %ss: %s", timeout, cmd)
            return None

        if proc.returncode != 0:
            logging.error(
                "Custom files_size_gatherer exited with %s: %s (stderr %.200r)",
                proc.returncode,
                cmd,
                stderr.decode(errors="replace"),
            )
            return None

        try:
            size_str = stdout.decode().strip()
        except Exception:
            logging.error("Custom files_size_gatherer produced non-text stdout")
            return None

        try:
            size = int(size_str)
        except ValueError:
            logging.error("Custom files_size_gatherer output is not an integer: %r", size_str)
            return None

        if size < 0:
            logging.error("Custom files_size_gatherer returned negative size: %s", size)
            return None

        return size
    except Exception as exc:
        logging.error(
            "files_size_gatherer failed for %s: %r",
            model.key.id,
            exc,
        )
