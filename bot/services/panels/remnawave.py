"""Async Remnawave API adapter used by the staged XUI migration."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aiohttp

from .base import BaseVPNClient, VPNAPIError

logger = logging.getLogger(__name__)


class RemnawaveClient(BaseVPNClient):
    """Compatibility adapter for Remnawave's official `/api` contract."""

    def __init__(self, server: dict):
        self.server = server
        raw_url = str(server.get("panel_api_url") or "").strip()
        if not raw_url:
            protocol = server.get("protocol", "https")
            raw_url = f"{protocol}://{server['host']}:{server['port']}"
        self.base_url = raw_url.rstrip("/")
        self.token = str(server.get("panel_api_token") or "").strip()
        self.squad_uuid = str(server.get("panel_squad_uuid") or "").strip()
        self.write_mode = str(server.get("panel_write_mode") or "disabled").lower()
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10, connect=4, sock_read=8)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        if not self.token:
            raise VPNAPIError("Remnawave API token is not configured")
        session = await self._ensure_session()
        headers = dict(kwargs.pop("headers", {}))
        headers.update({"Authorization": f"Bearer {self.token}", "Accept": "application/json"})
        try:
            async with session.request(method, f"{self.base_url}{path}", headers=headers, **kwargs) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    message = payload.get("message") if isinstance(payload, dict) else str(payload)
                    raise VPNAPIError(f"Remnawave HTTP {response.status}: {message}")
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise VPNAPIError(f"Remnawave is unreachable: {exc}") from exc
        return payload.get("response", payload) if isinstance(payload, dict) else payload

    def _assert_write_allowed(self, username: str) -> None:
        if self.write_mode == "production":
            return
        if self.write_mode == "shadow" and username.startswith("arc-staging-"):
            return
        raise VPNAPIError(
            "Remnawave writes are disabled; use shadow mode for arc-staging-* users or explicit production cutover"
        )

    @staticmethod
    def _username(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", value or "")[:36]
        return cleaned if len(cleaned) >= 3 else f"arc_{cleaned or 'user'}"

    async def login(self) -> bool:
        await self._request("GET", "/api/nodes")
        return True

    async def get_inbounds(self) -> List[Dict[str, Any]]:
        nodes = await self._request("GET", "/api/nodes")
        return nodes if isinstance(nodes, list) else []

    async def get_server_status(self) -> Dict[str, Any]:
        nodes = await self.get_inbounds()
        target = self.server.get("panel_node_uuid")
        if target:
            nodes = [node for node in nodes if str(node.get("uuid")) == str(target)]
        return {"online": any(node.get("isConnected") for node in nodes), "nodes": nodes}

    async def get_stats(self) -> Dict[str, Any]:
        result = await self._request("GET", "/api/users", params={"start": 0, "size": 1})
        return {"users": int(result.get("total", 0)), "panel": "remnawave"}

    async def get_online_clients_count(self) -> int:
        result = await self._request("GET", "/api/users", params={"start": 0, "size": 500})
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=3)
        count = 0
        for user in result.get("users", []):
            raw = (user.get("userTraffic") or {}).get("onlineAt")
            if raw:
                try:
                    count += datetime.fromisoformat(raw.replace("Z", "+00:00")) >= cutoff
                except ValueError:
                    pass
        return int(count)

    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            return await self._request("GET", f"/api/users/by-username/{self._username(username)}")
        except VPNAPIError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise

    async def get_user_by_vless_uuid(self, vless_uuid: str) -> Optional[Dict[str, Any]]:
        """Compatibility lookup for ArcVPN's legacy delete(inbound, vless_uuid) contract."""
        start = 0
        while start < 5000:  # bounded safety fallback; normal writes use username
            result = await self._request("GET", "/api/users", params={"start": start, "size": 500})
            users = result.get("users", [])
            for user in users:
                if str(user.get("vlessUuid")) == str(vless_uuid):
                    return user
            start += len(users)
            if not users or start >= int(result.get("total", 0)):
                return None
        raise VPNAPIError("VLESS UUID lookup exceeded 5000 users; migrate caller to panel user ID")

    async def set_user_squads_and_limit(
        self, username: str, squad_uuids: List[str], traffic_limit_bytes: int,
        *, expiry_at: Optional[str] = None, enabled: bool = True,
    ) -> Dict[str, Any]:
        """Apply the complete isolated access boundary and verify it."""
        user = await self._user_for_write(username)
        payload: Dict[str, Any] = {
            "id": user["id"],
            "status": "ACTIVE" if enabled else "DISABLED",
            "trafficLimitBytes": max(0, int(traffic_limit_bytes)),
            "trafficLimitStrategy": "NO_RESET",
            "activeInternalSquads": list(dict.fromkeys(squad_uuids)),
        }
        if expiry_at:
            payload["expireAt"] = expiry_at
        await self._request("PATCH", "/api/users", json=payload)
        verified = await self.get_user(username)
        if not verified:
            raise VPNAPIError("Remnawave user disappeared after update")
        return verified

    async def add_client(self, inbound_id: int, email: str, total_gb: int = 0, expire_days: int = 30,
                         limit_ip: int = 1, enable: bool = True, tg_id: str = "", flow: str = "") -> Dict[str, Any]:
        username = self._username(email)
        self._assert_write_allowed(username)
        payload: Dict[str, Any] = {
            "username": username,
            "status": "ACTIVE" if enable else "DISABLED",
            # ArcVPN meters only the separately provisioned LTE identity.
            "trafficLimitBytes": 0,
            "trafficLimitStrategy": "NO_RESET",
            "expireAt": (datetime.now(timezone.utc) + timedelta(days=expire_days)).isoformat(),
            "hwidDeviceLimit": max(0, int(limit_ip)),
            "vlessUuid": str(uuid.uuid4()),
            "description": "ArcVPN staged migration",
        }
        if tg_id and str(tg_id).isdigit():
            payload["telegramId"] = int(tg_id)
        if self.squad_uuid:
            payload["activeInternalSquads"] = [self.squad_uuid]
        return await self._request("POST", "/api/users", json=payload)

    async def get_inbound_flow(self, inbound_id: int) -> str:
        return ""

    async def get_client_stats(self, email: str) -> Optional[Dict[str, Any]]:
        user = await self.get_user(email)
        if not user:
            return None
        traffic = user.get("userTraffic") or {}
        used = int(traffic.get("usedTrafficBytes") or 0)
        return {
            "email": user.get("username"), "id": user.get("vlessUuid"),
            "up": 0, "down": used, "total": int(user.get("trafficLimitBytes") or 0),
            "expiryTime": user.get("expireAt"), "enable": user.get("status") == "ACTIVE",
            "panel_user_id": user.get("id"), "subscriptionUrl": user.get("subscriptionUrl"),
        }

    async def _user_for_write(self, email: str) -> Dict[str, Any]:
        username = self._username(email)
        self._assert_write_allowed(username)
        user = await self.get_user(username)
        if not user:
            raise VPNAPIError(f"Remnawave user not found: {username}")
        return user

    async def delete_client(self, inbound_id: int, client_uuid: str) -> bool:
        user = await self.get_user_by_vless_uuid(client_uuid)
        if not user:
            return True
        self._assert_write_allowed(self._username(user["username"]))
        await self._request("DELETE", f"/api/users/{user['id']}")
        return True

    async def reset_client_traffic(self, inbound_id: int, email: str) -> bool:
        user = await self._user_for_write(email)
        await self._request("POST", f"/api/users/{user['id']}/actions/reset-traffic")
        return True

    async def update_client_traffic_limit(self, inbound_id: int, client_uuid: str, email: str, total_gb: int) -> bool:
        return await self.update_client_limit(inbound_id, client_uuid, email, int(total_gb) * 1024 ** 3)

    async def disable_reset_for_all_clients(self) -> int:
        raise VPNAPIError("Bulk production writes are not enabled during migration")

    async def extend_client_expiry(self, inbound_id: int, client_uuid: str, email: str, days: int) -> bool:
        user = await self._user_for_write(email)
        current = datetime.fromisoformat(str(user["expireAt"]).replace("Z", "+00:00"))
        expiry = max(current, datetime.now(timezone.utc)) + timedelta(days=days)
        await self._request("PATCH", "/api/users", json={"id": user["id"], "expireAt": expiry.isoformat()})
        return True

    async def get_client_config(self, email: str) -> Optional[Dict[str, Any]]:
        user = await self.get_user(email)
        return {"subscriptionUrl": user.get("subscriptionUrl"), "user": user} if user else None

    async def get_subscription_link(self, sub_id: str) -> Optional[str]:
        return None

    async def get_database_backup(self) -> bytes:
        raise VPNAPIError("Remnawave backups are managed by its PostgreSQL backup workflow")

    async def update_client_limit(self, inbound_id: int, client_uuid: str, email: str, total_gb_bytes: int) -> bool:
        user = await self._user_for_write(email)
        await self._request("PATCH", "/api/users", json={"id": user["id"], "trafficLimitBytes": 0})
        return True

    async def update_client_full(self, inbound_id: int, client_uuid: str, email: str, expiry_time_ms: int,
                                 total_gb_bytes: int, enable: bool = True, limit_ip: int = 1, **_: Any) -> bool:
        user = await self._user_for_write(email)
        payload: Dict[str, Any] = {
            "id": user["id"], "status": "ACTIVE" if enable else "DISABLED",
            "trafficLimitBytes": 0, "hwidDeviceLimit": max(0, int(limit_ip)),
        }
        if expiry_time_ms:
            payload["expireAt"] = datetime.fromtimestamp(expiry_time_ms / 1000, timezone.utc).isoformat()
        await self._request("PATCH", "/api/users", json=payload)
        return True

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
