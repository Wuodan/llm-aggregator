"""Command line interface for llm-aggregator."""

from .main import main as _main


def main() -> None:
    """Delegate to the main server runner."""
    _main()


__all__ = ["main"]
