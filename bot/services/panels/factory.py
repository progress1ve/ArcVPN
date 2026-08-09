"""Panel client registry. XUI remains the default until an explicit cutover."""
from typing import Any, Dict, Type

from .base import BaseVPNClient, VPNAPIError
from .xui import XUIClient
from .marzban import MarzbanClient
from .remnawave import RemnawaveClient

PANEL_CLIENTS: Dict[str, Type[BaseVPNClient]] = {
    "xui": XUIClient,
    "3x-ui": XUIClient,
    "remnawave": RemnawaveClient,
    "marzban": MarzbanClient,
}


def panel_type(server: Dict[str, Any]) -> str:
    return str(server.get("panel_type") or "xui").strip().lower()


def create_panel_client(server: Dict[str, Any]) -> BaseVPNClient:
    kind = panel_type(server)
    client_class = PANEL_CLIENTS.get(kind)
    if client_class is None:
        raise VPNAPIError(f"Unsupported VPN panel type: {kind}")
    return client_class(server)


def panel_cache_key(server: Dict[str, Any]) -> tuple:
    """Invalidate cached clients when connection settings or panel type change."""
    return (
        int(server["id"]), panel_type(server), server.get("panel_api_url"),
        server.get("host"), server.get("port"), server.get("web_base_path"),
    )
