from __future__ import annotations

from Base.Repository.register import register_base_module_connection, register_default_connection

_connections_registered = False


def ensure_default_connections_registered() -> None:
    """Register default repository connections explicitly and only once."""
    global _connections_registered
    if _connections_registered:
        return

    register_default_connection()
    register_base_module_connection()
    _connections_registered = True


__all__ = [
    "ensure_default_connections_registered",
    "register_base_module_connection",
    "register_default_connection",
]
