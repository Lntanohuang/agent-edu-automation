"""
LangSmith tracing helpers.
Gracefully degrades to no-op when langsmith is unavailable.
"""
from collections.abc import Callable
from typing import Any


try:
    from langsmith import traceable as _traceable  # type: ignore
except Exception:
    _traceable = None


def traceable(*args: Any, **kwargs: Any) -> Callable:
    """A safe wrapper around langsmith.traceable."""

    def _identity_decorator(func: Callable) -> Callable:
        return func

    if _traceable is None:
        return _identity_decorator
    return _traceable(*args, **kwargs)
