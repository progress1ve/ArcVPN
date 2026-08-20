#!/usr/bin/env python3
"""Build a compact, deterministic provider comparison from ArcVPN telemetry."""

import argparse
import contextlib
import datetime as dt
import json
import math
import sqlite3
from pathlib import Path


METRICS = (
    "latency_ms", "cpu_steal_pct", "packet_loss_pct", "jitter_ms", "dns_ms",
    "https_ms", "download_mbps",
)

REQUIRED_THRESHOLDS = {
    "packet_loss_pct": ("p95", 1, "max"),
    "jitter_ms": ("p95", 20, "max"),
    "cpu_steal_pct": ("p95", 5, "max"),
    "download_mbps": ("p10", 100, "min"),
}


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


def _parse_sample_time(value):
    if isinstance(value, dt.datetime):
        return value
    return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _metric_summary(samples):
    return {
        metric: {
            "p10": percentile([sample[metric] for sample in samples], 0.10),
            "p50": percentile([sample[metric] for sample in samples], 0.50),
            "p95": percentile([sample[metric] for sample in samples], 0.95),
        }
        for metric in METRICS
    }


def _threshold_failures(metrics):
    failures = []
    for metric, (percentile_name, threshold, direction) in REQUIRED_THRESHOLDS.items():
        value = metrics[metric][percentile_name]
        if value is None:
            failures.append(f"{metric}.{percentile_name}=missing")
        elif direction == "max" and value > threshold:
            failures.append(f"{metric}.{percentile_name}={value}>{threshold}")
        elif direction == "min" and value < threshold:
            failures.append(f"{metric}.{percentile_name}={value}<{threshold}")
    return failures


def build_report(db_path: Path, hours: int, source: str = "agent", evening_start_utc=15, evening_end_utc=21):
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
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
        metrics = _metric_summary(samples)
        evening_samples = [
            sample for sample in samples
            if evening_start_utc <= _parse_sample_time(sample["sampled_at"]).hour < evening_end_utc
        ]
        evening_metrics = _metric_summary(evening_samples) if evening_samples else None
        expected = max(1, int(hours * 6))
        coverage_pct = round(min(100, len(samples) / expected * 100), 2)
        failures = _threshold_failures(metrics)
        if len(samples) < expected * 0.95:
            failures.append(f"coverage_pct={coverage_pct}<95")
        if not evening_samples:
            failures.append("evening_window=missing")
        report["nodes"][host] = {
            "samples": len(samples),
            "coverage_pct": coverage_pct,
            "metrics": metrics,
            "evening_utc": {
                "start_hour": evening_start_utc,
                "end_hour": evening_end_utc,
                "samples": len(evening_samples),
                "metrics": evening_metrics,
            },
            "canary_ready": not failures,
            "gate_failures": failures,
        }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="/root/ArcVPN/database/vpn_bot.db")
    parser.add_argument("--hours", type=int, default=72)
    parser.add_argument("--source", default="agent")
    parser.add_argument("--evening-start-utc", type=int, default=15)
    parser.add_argument("--evening-end-utc", type=int, default=21)
    parser.add_argument("--output")
    args = parser.parse_args()
    if not 0 <= args.evening_start_utc < args.evening_end_utc <= 24:
        parser.error("evening UTC window must satisfy 0 <= start < end <= 24")
    report = build_report(
        Path(args.db), max(1, args.hours), args.source,
        args.evening_start_utc, args.evening_end_utc,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
