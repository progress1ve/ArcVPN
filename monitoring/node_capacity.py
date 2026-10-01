"""Conservative capacity summaries from independent agent telemetry."""
from __future__ import annotations

import math
from datetime import datetime

MIN_SAMPLES = {"15m": 3, "1h": 12, "6h": 36, "24h": 72, "7d": 100}
MIN_SPAN_SECONDS = {"15m": 600, "1h": 2700, "6h": 14400,
                    "24h": 64800, "7d": 432000}


def percentile(values: list[float], fraction: float) -> float | None:
    clean = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)) and value >= 0)
    return clean[math.floor((len(clean) - 1) * fraction)] if clean else None


def summarize(samples: list[dict], capacity: dict[str, float | None], period: str) -> dict:
    if period not in MIN_SAMPLES:
        raise ValueError("invalid_period")
    timestamps = []
    for item in samples:
        raw = item.get("sampled_at")
        if raw:
            try:
                timestamps.append(datetime.fromisoformat(str(raw).replace("Z", "+00:00")))
            except ValueError:
                pass
    coverage_ok = (len(samples) >= MIN_SAMPLES[period] and len(timestamps) >= MIN_SAMPLES[period]
                   and (max(timestamps) - min(timestamps)).total_seconds() >= MIN_SPAN_SECONDS[period])
    p95 = {key: percentile([item.get(key) for item in samples], .95)
           for key in ("cpu_pct", "mem_pct", "net_rx_bps", "net_tx_bps")}
    network = {}
    for direction, field in (("rx", "net_rx_bps"), ("tx", "net_tx_bps")):
        confirmed = capacity.get(direction)
        observed = p95[field] / 1_000_000 if p95[field] is not None else None
        usable = confirmed is not None and confirmed > 0 and coverage_ok and observed is not None
        network[direction] = {
            "confirmed_mbps": confirmed,
            "observed_p95_mbps": round(observed, 2) if observed is not None else None,
            "headroom_pct": round(max(0, 100 * (1 - observed / confirmed)), 1) if usable else None,
            "spare_mbps": round(max(0, confirmed - observed), 2) if usable else None,
        }
    warnings = []
    if coverage_ok and period in {"6h", "24h", "7d"}:
        for direction, value in network.items():
            headroom = value["headroom_pct"]
            if headroom is not None and headroom < 15:
                warnings.append(f"{direction}_capacity_critical")
            elif headroom is not None and headroom < 30:
                warnings.append(f"{direction}_capacity_low")
        if p95["cpu_pct"] is not None and p95["cpu_pct"] >= 85:
            warnings.append("cpu_sustained_high")
        if p95["mem_pct"] is not None and p95["mem_pct"] >= 90:
            warnings.append("memory_sustained_high")
    return {"period": period, "samples": len(samples), "coverage_ok": coverage_ok,
            "p95": {key: round(value, 2) if value is not None else None for key, value in p95.items()},
            "network": network, "warnings": warnings,
            "additional_users": None, "additional_users_reason": "missing_historical_per_user_demand"}


def network_user_estimate(summary: dict, benchmark: list[dict], demand_mbps: float) -> dict | None:
    """Explicit network-only scenario, never a confirmed comfortable-user limit."""
    if not summary["coverage_ok"] or len(benchmark) != 5 or len({row.get('city') for row in benchmark}) != 5 or any(not row.get("valid") for row in benchmark):
        return None
    if not math.isfinite(demand_mbps) or not 1 <= demand_mbps <= 100:
        raise ValueError("invalid_demand")
    observed = summary["network"]["tx"]["observed_p95_mbps"]
    cpu, memory = summary['p95']['cpu_pct'], summary['p95']['mem_pct']
    if observed is None or cpu is None or memory is None:
        return None
    measured = min(row['receiver_mbps'] for row in benchmark)
    spare = max(0, measured * .7 - observed)
    additional = math.floor(spare / demand_mbps) if cpu < 85 and memory < 90 else 0
    return {"additional_users":additional,"assumed_mbps_per_user":demand_mbps,
            "reserve_pct":30,"measured_floor_mbps":measured,"observed_p95_mbps":observed,
            "scope":"node_to_russia_network_only","verified_user_capacity":False}
