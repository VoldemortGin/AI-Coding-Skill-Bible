#!/usr/bin/env python3
"""Scaffold a conforming polyglot monorepo (polyglot-core-standard).

Usage:
    python scaffold.py <repo_name> [--target DIR] [--core rust] [--hosts swift python ...]

Example:
    python scaffold.py acme --target ~/code --hosts swift python

Mirrors assets/templates/ into <target>/<repo_name>/, substituting the SOLE placeholder
`__REPO__` in BOTH file contents and file/dir names (e.g. core/crates/__REPO__-core,
apple/Sources/__REPO__/, the `__REPO__._native` module). Always emits the Rust `core/` (the
single source of truth) + the root composed gate; emits one host sub-tree per `--host`
(swift→apple, python→python, kotlin→android) and prunes the composed gate + version matrix to
match. Then per-sub-tree, scaffold the FULL internals with each sibling standard's own
scaffold, and run `make check` (the one composed gate) to verify.
"""
from __future__ import annotations

import argparse
import re
import stat
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
PLACEHOLDER = "__REPO__"

# host (language) → its sub-tree directory in the template tree
HOST_DIRS = {"swift": "apple", "python": "python", "kotlin": "android"}
# every directory that IS a host sub-tree (skipped unless its host was requested)
ALL_HOST_DIRS = set(HOST_DIRS.values())
# stable order for the Makefile `check-hosts:` prerequisites
HOST_DIR_ORDER = ["apple", "python", "android"]


def _valid_name(name: str) -> bool:
    # Used as a Rust crate-name segment, a Swift module, and a Python package — must be a plain
    # identifier (no hyphens) starting with a letter.
    return name.isidentifier() and name[0].isalpha()


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _prune_makefile(makefile: Path, host_dirs: set[str]) -> None:
    """Rewrite the `check-hosts:` line so it depends only on the selected hosts' gates."""
    deps = " ".join(f"check-{d}" for d in HOST_DIR_ORDER if d in host_dirs)
    repl = f"check-hosts: {deps} " if deps else "check-hosts: "
    text = makefile.read_text(encoding="utf-8")
    text = re.sub(r"^check-hosts:[^#\n]*", repl, text, count=1, flags=re.M)
    makefile.write_text(text, encoding="utf-8")


def _prune_versions(versions: Path, host_dirs: set[str]) -> None:
    """Drop unselected hosts' lines from the [bindings] section of versions.toml."""
    out: list[str] = []
    section: str | None = None
    for line in versions.read_text(encoding="utf-8").splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
        if section == "bindings" and "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            if key in ALL_HOST_DIRS and key not in host_dirs:
                continue  # this host was not requested — drop its binding-posture line
        out.append(line)
    versions.write_text("".join(out), encoding="utf-8")


def scaffold(repo: str, target: Path, hosts: list[str]) -> None:
    if not _valid_name(repo):
        raise SystemExit(
            f"invalid repo name (must be a plain identifier starting with a letter): {repo!r}"
        )

    host_dirs: set[str] = set()
    for host in hosts:
        if host not in HOST_DIRS:
            raise SystemExit(f"unknown host {host!r}; choose from {sorted(HOST_DIRS)}")
        host_dirs.add(HOST_DIRS[host])

    skipped = ALL_HOST_DIRS - host_dirs
    # Requested hosts that have no template sub-tree yet (e.g. kotlin/android).
    missing = {d for d in host_dirs if not (TEMPLATES / d).is_dir()}

    # 1. Mirror the template tree, substituting __REPO__ in contents AND in path names.
    copied = 0
    for src in sorted(TEMPLATES.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(TEMPLATES)
        if rel.parts[0] in skipped:
            continue  # host not requested
        dst = target / Path(str(rel).replace(PLACEHOLDER, repo))
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8").replace(PLACEHOLDER, repo), encoding="utf-8")
        if src.name.endswith(".sh"):
            _make_executable(dst)
        copied += 1

    # 2. Prune the composed gate + version matrix to exactly the selected hosts.
    _prune_makefile(target / "Makefile", host_dirs)
    _prune_versions(target / "versions.toml", host_dirs)

    _print_next_steps(repo, target, host_dirs, missing, copied)


def _print_next_steps(
    repo: str, target: Path, host_dirs: set[str], missing: set[str], copied: int
) -> None:
    present = sorted(d for d in host_dirs if d not in missing)
    print(f"✓ scaffolded polyglot monorepo: {target}  ({copied} files)")
    print(f"  core/ (Rust, single source of truth) + hosts: {', '.join(present) or '(none)'}")
    if missing:
        print(f"  ⚠ no template sub-tree yet for: {', '.join(sorted(missing))} "
              "(add it under assets/templates/ to support this host)")
    print("")
    print("  next steps:")
    print(f"    cd {target}")
    print("    make gen-bindings   # derive host bindings from the core (single source of truth)")
    print("    make check          # the ONE composed gate: core + hosts + binding freshness")
    print("")
    print("  flesh out each sub-tree with its sibling standard's own scaffold (FULL internals):")
    print("    core/   → rust-project-standard    (domain / kernel / adapters, cargo-deny, …)")
    if "apple" in host_dirs:
        print("    apple/  → swift-project-standard   (Package.swift / xcodebuild, Domain target, …)")
    if "python" in host_dirs:
        print("    python/ → python-project-standard  (uv, beartype, full pytest gate, …)")
    print("")
    print("  a contract change is a multi-sub-tree change: ADR first → edit core →")
    print("  make gen-bindings → adapt every host wrapper → make check → ONE commit.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a conforming polyglot monorepo (polyglot-core-standard)."
    )
    parser.add_argument("repo", help="repo name (plain identifier, e.g. acme)")
    parser.add_argument("--target", default=".", help="parent directory (default: current)")
    parser.add_argument(
        "--core", default="rust", choices=["rust"], help="core language (only rust is supported)"
    )
    parser.add_argument(
        "--hosts",
        nargs="*",
        default=["swift", "python"],
        help="host languages: swift→apple, python→python, kotlin→android",
    )
    args = parser.parse_args()
    target = Path(args.target).resolve() / args.repo  # mirror into <target>/<repo>/
    scaffold(args.repo, target, list(args.hosts))


if __name__ == "__main__":
    main()
