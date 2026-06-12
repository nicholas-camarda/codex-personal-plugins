
"""Late-bound reference to the workspace_governor entry module."""
from __future__ import annotations

from typing import Any

_MODULE: Any = None

def bind(module: Any) -> None:
    global _MODULE
    _MODULE = module

def wg():
    if _MODULE is None:
        raise RuntimeError("wg_core host module is not bound")
    return _MODULE
