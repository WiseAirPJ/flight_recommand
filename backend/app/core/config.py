"""Compatibility import for infrastructure modules; settings live in one place."""

from app.config.settings import Settings, settings

__all__ = ["Settings", "settings"]
