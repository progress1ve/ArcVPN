#!/usr/bin/env python3
"""Build a compact, deterministic provider comparison from ArcVPN telemetry."""

import argparse
import json
import math
import sqlite3
from pathlib import Path


METRICS = (
    "cpu_steal_pct", "packet_loss_pct", "jitter_ms", "dns_ms",
    "https_ms", "download_mbps",
)


def percentile(values, fraction):
    values = sorted(float(value) for value in values if value is not None)
    if not values:
        return None
    position = (len(values) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return round(values[low], 2)
    return round(values[low] + (values[high] - values[low]) * (position - low), 2)


def build_report(db_path: Path, hours: int, source: str = "agent"):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""SELECT host,sampled_at,{','.join(METRICS)}
                FROM server_health_samples
                WHERE source=? AND sampled_at >= datetime('now', ?)
                ORDER BY sampled_at""",
            (source, f"-{hours} hours"),
        ).fetchall()
    grouped = {}
    for row in rows:
        grouped.setdefault(row["host"], []).append(row)
    report = {"window_hours": hours, "nodes": {}}
    for host, samples in grouped.items():
        metrics = {}
        for metric in METRICS:
            values = [sample[metric] for sample in samples]
            metrics[metric] = {
                "p10": percentile(values, 0.10),
                "p50": percentile(values, 0.50),
                "p95": percentile(values, 0.95),
            }
        expected = max(1, int(hours * 6))
        report["nodes"][host] = {
            "samples": len(samples),
            "coverage_pct": round(min(100, len(samples) / expected * 100), 2),
            "metrics": metrics,
            "canary_ready": (
                len(samples) >= expected * 0.95
                and (metrics["packet_loss_pct"]["p95"] or 0) <= 1
                and (metrics["jitter_ms"]["p95"] or 0) <= 20
                and (metrics["cpu_steal_pct"]["p95"] or 0) <= 5
                and (metrics["download_mbps"]["p10"] or 0) >= 100
            ),
        }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="/root/ArcVPN/database/vpn_bot.db")
    parser.add_argument("--hours", type=int, default=72)
    parser.add_argument("--source", default="agent")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build_report(Path(args.db), max(1, args.hours), args.source)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
