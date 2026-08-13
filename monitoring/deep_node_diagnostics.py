#!/usr/bin/env python3
"""Bounded, dependency-free network diagnostics for an ArcVPN node."""

import argparse
import json
import socket
import statistics
import time


def tcp_probe(address: str, port: int, attempts: int = 3) -> dict:
    values = []
    errors = []
    for _ in range(attempts):
        started = time.monotonic()
        try:
            with socket.create_connection((address, port), timeout=4):
                values.append((time.monotonic() - started) * 1000)
        except OSError as exc:
            errors.append(type(exc).__name__)
    return {
        "port": port,
        "ok": bool(values),
        "success": len(values),
        "attempts": attempts,
        "latency_p50_ms": round(statistics.median(values), 2) if values else None,
        "latency_max_ms": round(max(values), 2) if values else None,
        "error": errors[-1] if errors else None,
    }


def run(host: str, ports: list[int]) -> dict:
    started = time.monotonic()
    try:
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, None)})
    except OSError as exc:
        return {"ok": False, "host": host, "addresses": [], "error": type(exc).__name__, "ports": []}
    probes = [tcp_probe(host, port) for port in sorted(set(ports))]
    return {
        "ok": bool(probes) and all(item["ok"] for item in probes),
        "host": host,
        "addresses": addresses,
        "duration_ms": round((time.monotonic() - started) * 1000, 2),
        "ports": probes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--ports", required=True)
    args = parser.parse_args()
    ports = [int(value) for value in args.ports.split(",") if value.strip().isdigit()]
    print(json.dumps(run(args.host, ports), ensure_ascii=False))


if __name__ == "__main__":
    main()
