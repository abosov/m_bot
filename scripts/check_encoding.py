#!/usr/bin/env python3
"""Scan repository files for UTF-8 decode issues and common mojibake artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterator

TEXT_EXTENSIONS = {
    ".py",
    ".sql",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".env",
    ".txt",
}

IGNORE_DIRS = {
    "specialist",
    "media",
    "static",
    ".git",
    ".venv",
    "__pycache__",
}

EXCLUDED_FILENAMES = {
    ".DS_Store",
}

MOJIBAKE_PATTERNS = (
    "\u00d0",
    "\u00d1",
    "\u00c3",
    "\u00c2",
    "\u00e2\u20ac\u2122",
    "\u00e2\u20ac\u0153",
    "\u00e2\u20ac",
    "\u00e2\u20ac\u201c",
    "\u00e2\u20ac\u201d",
    "\u00e2\u20ac\u00a6",
)


def iter_files(repo_root: Path, requested_paths: list[str] | None = None) -> Iterator[Path]:
    if requested_paths:
        roots = [resolve_requested_path(repo_root, p) for p in requested_paths]
    else:
        roots = [repo_root]

    seen: set[Path] = set()
    for root in roots:
        if root.is_file():
            resolved = root.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield root
            continue

        for path in root.rglob("*"):
            if not path.is_file() or path.name in EXCLUDED_FILENAMES:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def resolve_requested_path(repo_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    path = candidate if candidate.is_absolute() else repo_root / candidate
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {raw_path}")
    return path


def should_skip_file(path: Path) -> bool:
    if any(part in IGNORE_DIRS for part in path.parts):
        return True
    if path.name in EXCLUDED_FILENAMES:
        return True
    suffix = path.suffix.lower()
    if path.name == ".env":
        return False
    return suffix not in TEXT_EXTENSIONS


def rel_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def compact(text: str, max_len: int = 120) -> str:
    one_line = " ".join(text.strip().split())
    if len(one_line) <= max_len:
        return one_line
    return one_line[: max_len - 1] + "…"


def extract_mojibake_contexts(decoded_text: str, limit: int = 3) -> list[str]:
    contexts: list[str] = []
    for line in decoded_text.splitlines():
        if any(pattern in line for pattern in MOJIBAKE_PATTERNS):
            context = compact(line)
            if context and context not in contexts:
                contexts.append(context)
        if len(contexts) >= limit:
            break
    return contexts


def scan_file(path: Path, repo_root: Path) -> tuple[list[str], list[str]]:
    fails: list[str] = []
    warns: list[str] = []
    path_for_output = rel_path(path, repo_root)

    try:
        raw = path.read_bytes()
    except OSError as exc:
        fails.append(f"FAIL read {path_for_output}: {exc}")
        return fails, warns

    try:
        decoded = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        fails.append(
            f"FAIL utf8 {path_for_output}: byte={exc.start} reason={exc.reason}"
        )
        return fails, warns

    if "\ufffd" in decoded:
        replacement_count = decoded.count("\ufffd")
        fails.append(
            f"FAIL replacement-char {path_for_output}: found={replacement_count} U+FFFD"
        )

    contexts = extract_mojibake_contexts(decoded)
    if contexts:
        warns.append(f"WARN mojibake {path_for_output}: " + " | ".join(contexts))

    return fails, warns


def run_scan(repo_root: Path, paths: list[str] | None, strict_warn: bool) -> int:
    total_files = 0
    skipped_files = 0
    all_fails: list[str] = []
    all_warns: list[str] = []

    for file_path in iter_files(repo_root=repo_root, requested_paths=paths):
        if should_skip_file(file_path):
            skipped_files += 1
            continue
        total_files += 1
        fails, warns = scan_file(file_path, repo_root=repo_root)
        all_fails.extend(fails)
        all_warns.extend(warns)

    for fail in all_fails:
        print(fail)
    for warn in all_warns:
        print(warn)

    print(
        f"SUMMARY scanned={total_files} skipped={skipped_files} fail={len(all_fails)} warn={len(all_warns)} strict_warn={strict_warn}"
    )

    if all_fails:
        return 1
    if strict_warn and all_warns:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check files for UTF-8 decoding issues and mojibake patterns."
    )
    parser.add_argument(
        "--strict-warn",
        action="store_true",
        help="Treat warnings as failures (non-zero exit code).",
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        default=None,
        metavar="PATH",
        help="Restrict scanning to specific files/directories (relative to repo root by default).",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    try:
        exit_code = run_scan(repo_root=Path.cwd(), paths=args.paths, strict_warn=args.strict_warn)
    except FileNotFoundError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        sys.exit(2)
    sys.exit(exit_code)
