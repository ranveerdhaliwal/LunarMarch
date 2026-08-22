#!/usr/bin/env python3
"""Install LunarMarch for user-wide or repository-scoped Codex discovery."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_NAME = "lunar-march"
SOURCE_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ENTRIES = (
    "SKILL.md",
    "LICENSE",
    "agents",
    "scripts",
    "references",
    "schemas",
    "examples",
    "evals",
)


class InstallError(RuntimeError):
    pass


def _iter_runtime_files(root: Path):
    for entry in RUNTIME_ENTRIES:
        path = root / entry
        if path.is_file():
            yield path.relative_to(root), path
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and "__pycache__" not in child.parts and child.suffix not in {".pyc", ".pyo"}:
                    yield child.relative_to(root), child


def bundle_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for relative, path in _iter_runtime_files(root):
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def validate_skill(root: Path) -> None:
    skill = root / "SKILL.md"
    if not skill.is_file():
        raise InstallError(f"SKILL.md is missing: {root}")
    text = skill.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "name: lunar-march" not in text.split("---", 2)[1]:
        raise InstallError(f"not a LunarMarch skill bundle: {root}")


def discover_repo_root(path: Path) -> Path:
    path = path.expanduser().resolve()
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    if path.is_dir():
        return path
    raise InstallError(f"repository root does not exist: {path}")


def destination_for(scope: str, repo_root: Path | None, destination: Path | None) -> Path:
    if destination is not None:
        return Path(os.path.abspath(destination.expanduser()))
    if scope == "user":
        return Path(os.path.abspath(Path.home() / ".agents" / "skills" / SKILL_NAME))
    if repo_root is None:
        raise InstallError("--repo-root is required for repo scope")
    return discover_repo_root(repo_root) / ".agents" / "skills" / SKILL_NAME


def inspect_installation(destination: Path) -> dict[str, Any]:
    lexists = os.path.lexists(destination)
    resolved = destination.resolve() if lexists else None
    valid = False
    fingerprint = None
    error = None
    if lexists:
        try:
            validate_skill(destination)
            fingerprint = bundle_fingerprint(destination)
            valid = True
        except (InstallError, OSError) as exc:
            error = str(exc)
    return {
        "destination": str(destination),
        "exists": lexists,
        "kind": "symlink" if destination.is_symlink() else "directory" if destination.is_dir() else "other" if lexists else None,
        "resolved": str(resolved) if resolved is not None else None,
        "valid": valid,
        "fingerprint": fingerprint,
        "error": error,
    }


def _copy_bundle(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    for entry in RUNTIME_ENTRIES:
        source_entry = source / entry
        target_entry = destination / entry
        if source_entry.is_dir():
            shutil.copytree(
                source_entry,
                target_entry,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
        elif source_entry.is_file():
            shutil.copy2(source_entry, target_entry)
    marker = {
        "format": "lunarmarch-install-v1",
        "source": str(source),
        "fingerprint": bundle_fingerprint(source),
    }
    (destination / ".lunarmarch-install.json").write_text(
        json.dumps(marker, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def install(
    destination: Path,
    mode: str,
    replace: bool = False,
    source: Path = SOURCE_ROOT,
) -> dict[str, Any]:
    source = source.resolve()
    # Preserve the destination's final symlink component. Resolving it would turn
    # an existing install into its source path and defeat idempotency checks.
    destination = Path(os.path.abspath(destination.expanduser()))
    validate_skill(source)
    if mode not in {"link", "copy"}:
        raise InstallError("mode must be link or copy")
    existing = inspect_installation(destination)
    source_fingerprint = bundle_fingerprint(source)
    if existing["exists"]:
        same_link = destination.is_symlink() and destination.resolve() == source
        same_copy = existing["valid"] and existing["fingerprint"] == source_fingerprint
        if (mode == "link" and same_link) or (mode == "copy" and same_copy):
            return {"status": "already-installed", "mode": mode, **existing}
        if not replace:
            raise InstallError(f"destination already exists with different content: {destination}")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = destination.with_name(f".{destination.name}.backup-{timestamp}")
        if os.path.lexists(backup):
            raise InstallError(f"backup destination already exists: {backup}")
        destination.rename(backup)
    else:
        backup = None
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "link":
        destination.symlink_to(source, target_is_directory=True)
    else:
        staging = Path(tempfile.mkdtemp(prefix=f".{SKILL_NAME}.", dir=destination.parent))
        try:
            staging.rmdir()
            _copy_bundle(source, staging)
            os.replace(staging, destination)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    installed = inspect_installation(destination)
    if not installed["valid"] or installed["fingerprint"] != source_fingerprint:
        raise InstallError("installed skill failed post-install integrity check")
    return {
        "status": "installed",
        "mode": mode,
        "backup": str(backup) if backup is not None else None,
        **installed,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install LunarMarch for Codex skill discovery")
    parser.add_argument("--scope", choices=["user", "repo"], default="user")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--destination", type=Path, help="exact destination override, primarily for testing")
    parser.add_argument("--mode", choices=["link", "copy"], help="default: link for user, copy for repo")
    parser.add_argument("--replace", action="store_true", help="move a differing install to a timestamped backup")
    parser.add_argument("--check", action="store_true", help="inspect without changing anything")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        destination = destination_for(args.scope, args.repo_root, args.destination)
        if args.check:
            print(json.dumps(inspect_installation(destination), indent=2, sort_keys=True))
            return 0
        mode = args.mode or ("link" if args.scope == "user" else "copy")
        print(json.dumps(install(destination, mode, args.replace), indent=2, sort_keys=True))
        return 0
    except (InstallError, OSError) as exc:
        print(f"install-lunarmarch: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
