"""Rerunnable UI entry point; the standalone host owns page configuration."""
from learnsignal import __version__
from learnsignal.ui import signal_theme
from learnsignal.ui.app import render

APP_INFO = {"product": "Learn Signal", "version": __version__, "repo": "research-prioritization", "slug": "learn"}
__all__ = ["APP_INFO", "render", "signal_theme"]
