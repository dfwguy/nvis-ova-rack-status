#!/usr/bin/env python3
"""Write a credential-safe file-level comparison of two source trees."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "deploy-secrets",
}
EXCLUDED_ROOTS = {".env", "docker-compose.override.yml"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def inventory(root: Path, excluded_paths: set[Path] | None = None) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    excluded_paths = excluded_paths or set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.resolve() in excluded_paths:
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if relative.as_posix() in EXCLUDED_ROOTS:
            continue
        name = path.name
        if name in {".DS_Store", "._.DS_Store"} or ".bak" in name or "prebak" in name:
            continue
        result[relative.as_posix()] = (path.stat().st_size, digest(path))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    output = args.output.resolve()
    original = inventory(args.original.resolve(), {output})
    current = inventory(args.current.resolve(), {output})
    names = sorted(original.keys() | current.keys())
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["status", "path", "original_bytes", "current_bytes", "original_sha256", "current_sha256"]
        )
        for name in names:
            before = original.get(name)
            after = current.get(name)
            if before is None:
                status = "added"
            elif after is None:
                status = "deleted"
            elif before[1] != after[1]:
                status = "modified"
            else:
                status = "unchanged"
            writer.writerow(
                [
                    status,
                    name,
                    before[0] if before else "",
                    after[0] if after else "",
                    before[1] if before else "",
                    after[1] if after else "",
                ]
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
