"""
Pipeline package - one method per stage from PIPELINE_STAGES.md.

`ChatPipeline` is exposed lazily via __getattr__ so that lightweight modules
(like `context_bundle`) can be imported without pulling in FastAPI/SQLAlchemy
through `chat_pipeline`. The router still uses `from app.pipeline import
ChatPipeline` exactly as before.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chat_pipeline import ChatPipeline  # noqa: F401

__all__ = ["ChatPipeline"]


def __getattr__(name: str):
    if name == "ChatPipeline":
        from .chat_pipeline import ChatPipeline as _ChatPipeline
        return _ChatPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
