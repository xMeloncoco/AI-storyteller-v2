"""
Pipeline package - one method per stage from PIPELINE_STAGES.md.

The HTTP routers should call ChatPipeline.run() / generate_more() and stay
thin. All per-stage logic lives here so each stage can be edited in isolation.
"""
from .chat_pipeline import ChatPipeline

__all__ = ["ChatPipeline"]
