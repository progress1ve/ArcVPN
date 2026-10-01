"""Bounded LatencyLab job client. Never include credentials or VPN URIs in errors."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://console.latencylab.ru"
OPERATORS = ("tmobile", "megafon", "beeline", "mts", "t2")


class LatencyLabError(RuntimeError):
    pass


class Client:
    def __init__(self, token: str, *, opener=urllib.request.urlopen, sleep=time.sleep):
        if not token.startswith("ll_"):
            raise LatencyLabError("invalid_api_key")
        self.token, self.opener, self.sleep = token, opener, sleep

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(BASE + path, data=body, method=method,
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json",
                     "Accept": "application/json", "User-Agent": "ArcVPN-LTE-Monitor/1"})
        try:
            with self.opener(request, timeout=30) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            raise LatencyLabError(f"http_{exc.code}") from None
        except (urllib.error.URLError, TimeoutError, ValueError):
            raise LatencyLabError("provider_unavailable") from None
        if not isinstance(result, dict) or result.get("ok") is False:
            raise LatencyLabError("provider_rejected_request")
        return result

    def job(self, path: str, payload: dict, *, polls: int = 30) -> dict:
        started = self.request("POST", path, payload)
        job_id = started.get("req_id")
        if not isinstance(job_id, str) or not job_id or len(job_id) > 128:
            raise LatencyLabError("missing_job_id")
        for _ in range(polls):
            self.sleep(2)
            current = self.request("GET", "/api/lab/job/" + urllib.parse.quote(job_id, safe=""))
            if current.get("status") == "done":
                result = current.get("result")
                if not isinstance(result, dict):
                    raise LatencyLabError("invalid_result")
                return result
            if current.get("status") in {"error", "cancelled", "failed"}:
                raise LatencyLabError("job_failed")
        raise LatencyLabError("job_timeout")

    def operators(self) -> set[str]:
        response = self.request("GET", "/api/lab/operators")
        online = (response.get("result") or {}).get("online") or []
        return {str(item) for item in online if str(item) in OPERATORS}

    def remaining_quota(self) -> int:
        response = self.request("GET", "/api/lab/account/stats")
        window = (response.get("result") or {}).get("window") or {}
        used, limit = window.get("used"), window.get("limit")
        if not isinstance(used, int) or not isinstance(limit, int):
            raise LatencyLabError("quota_unavailable")
        return max(0, limit - used)

    def vpn_multiscan(self, uri: str, operators: list[str]) -> dict:
        return self.job("/api/lab/vpn-key", {"uri": uri, "operator": "multiscan",
                         "operators": operators, "node_id": "orel"})

    def control_multiscan(self, target: str, operators: list[str]) -> dict:
        return self.job("/api/lab/multiscan", {"target": target, "operators": operators,
                         "ping_method": "tcp", "async": True, "node_id": "orel"})
