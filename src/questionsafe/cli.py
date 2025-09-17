from __future__ import annotations

# Thin forwarder to the real CLI app in the cli package
from .cli import app  # noqa: F401

if __name__ == "__main__":  # pragma: no cover
    app()
