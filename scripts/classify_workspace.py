#!/usr/bin/env python3
"""Classify every tracked/untracked workspace path without reading file contents."""

import argparse
import json
import subprocess
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]


def _git(*args):
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def classify(path, tracked):
    item = PurePosixPath(path.replace("\\", "/"))
    name = item.name.lower()
    parts = {part.lower() for part in item.parts}
    suffix = item.suffix.lower()

    if name in {".env", "__diag.py"} or name.startswith(".secret"):
        return "secret"
    if ".arcshots" in parts or ".codex-worktrees" in parts or "__pycache__" in parts:
        return "generated"
    if suffix in {".log", ".tmp", ".pyc"} or name.endswith(".out.log") or name.endswith(".err.log"):
        return "generated"
    if name.endswith(".backup") or name.startswith("vless_test_"):
        return "obsolete"
    if name.startswith("support_message_") or "diagnostic" in name or name.startswith("debug-"):
        return "diagnostic"
    if item.parts and item.parts[0].lower() in {"deploy", "monitoring"}:
        return "production_asset" if suffix in {".service", ".timer", ".conf"} else "source"
    if item.parts and item.parts[0].lower() == "webapp" and "public" in parts:
        return "production_asset"
    if suffix in {".py", ".js", ".ts", ".svelte", ".css", ".html", ".sql"}:
        return "source"
    if suffix in {".md", ".rst", ".txt"}:
        return "documentation" if tracked else "unknown"
    if suffix in {".png", ".jpg", ".jpeg", ".svg", ".webp", ".mp4"}:
        return "production_asset" if tracked else "unknown"
    if name in {"dockerfile", "makefile"} or suffix in {".json", ".toml", ".yaml", ".yml", ".ini"}:
        return "source" if tracked else "unknown"
    return "source" if tracked else "unknown"


def inventory():
    tracked = set(_git("ls-files"))
    untracked = set(_git("ls-files", "--others", "--exclude-standard"))
    deleted = {line[3:] for line in _git("status", "--short") if line[:2].strip() == "D"}
    rows = []
    for path in sorted(tracked | untracked):
        state = "tracked"
        if path in untracked:
            state = "untracked"
        elif path in deleted:
            state = "tracked_deleted"
        rows.append({"path": path, "state": state, "class": classify(path, path in tracked)})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    rows = inventory()
    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    print("| Path | Git state | Class |")
    print("|---|---|---|")
    for row in rows:
        safe_path = row["path"].replace("|", "\\|")
        print(f"| `{safe_path}` | {row['state']} | {row['class']} |")


if __name__ == "__main__":
    main()
