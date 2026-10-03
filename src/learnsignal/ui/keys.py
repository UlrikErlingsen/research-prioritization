"""Session-state and widget keys, namespaced with the Signal Hub slug, and the Hub-mode switch."""
import os

NS = "learn"


def k(name: str) -> str:
    """Return the namespaced key for a widget or session-state entry."""
    return f"{NS}:{name}"


def hub_mode() -> bool:
    """True inside Signal Hub, which sets SIGNAL_HUB=1 before importing apps."""
    return os.environ.get("SIGNAL_HUB") == "1"
