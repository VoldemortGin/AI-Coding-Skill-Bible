#!/usr/bin/env python3
"""Check structural invariants for a Rust/PyO3 Python package."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tomllib
from typing import Any


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def nested(data: dict[str, Any], *keys: str) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def cargo_manifests(root: Path) -> list[Path]:
    manifests: list[Path] = []
    for directory, names, files in os.walk(root):
        names[:] = [name for name in names if name not in {".git", ".venv", "target"}]
        if "Cargo.toml" in files:
            manifests.append(Path(directory) / "Cargo.toml")
    return manifests


def contains_text(value: Any, needle: str) -> bool:
    if isinstance(value, str):
        return needle in value
    if isinstance(value, dict):
        return any(
            needle in str(key) or contains_text(child, needle)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(contains_text(child, needle) for child in value)
    return False


def check(root: Path) -> list[str]:
    failures: list[str] = []
    cargo_path = root / "Cargo.toml"
    pyproject_path = root / "pyproject.toml"

    if not cargo_path.is_file():
        failures.append("missing Cargo.toml")
    if not pyproject_path.is_file():
        failures.append("missing pyproject.toml")
        return failures

    pyproject = load_toml(pyproject_path)
    backend = nested(pyproject, "build-system", "build-backend")
    if backend != "maturin":
        failures.append("[build-system].build-backend must be 'maturin'")

    package_name = nested(pyproject, "project", "name")
    if not isinstance(package_name, str) or not package_name:
        failures.append("[project].name must be set")
        package_name = ""

    module_name = nested(pyproject, "tool", "maturin", "module-name")
    if isinstance(module_name, str) and "." in module_name:
        import_name = module_name.split(".", maxsplit=1)[0]
    else:
        import_name = package_name.replace("-", "_")
    python_source = nested(pyproject, "tool", "maturin", "python-source")
    if python_source is None:
        source_root = root / "src"
    elif isinstance(python_source, str):
        source_root = root / python_source
    else:
        failures.append("[tool.maturin].python-source must be a string")
        source_root = root / "python"

    package_root = source_root / import_name
    if import_name and not package_root.is_dir():
        failures.append(f"missing import package: {package_root.relative_to(root)}")
    if import_name and not (package_root / "py.typed").is_file():
        failures.append(
            f"missing PEP 561 marker: {(package_root / 'py.typed').relative_to(root)}"
        )

    if not isinstance(module_name, str) or not module_name.startswith(
        f"{import_name}."
    ):
        failures.append(
            "[tool.maturin].module-name must place the extension inside the public package"
        )

    mypy = nested(pyproject, "tool", "mypy")
    if not isinstance(mypy, dict) or mypy.get("strict") is not True:
        failures.append("[tool.mypy].strict must be true")

    ruff = nested(pyproject, "tool", "ruff")
    if not isinstance(ruff, dict):
        failures.append("missing [tool.ruff] configuration")

    pytest_options = nested(pyproject, "tool", "pytest", "ini_options")
    warning_filters = (
        pytest_options.get("filterwarnings", [])
        if isinstance(pytest_options, dict)
        else []
    )
    if not any(str(item).strip() == "error" for item in warning_filters):
        failures.append("pytest must treat warnings as errors")

    if not any((root / name).is_file() for name in ("ci.sh", "Makefile")):
        failures.append("missing root ci.sh or Makefile quality gate")

    requires_python = nested(pyproject, "project", "requires-python")
    if not isinstance(requires_python, str):
        failures.append("[project].requires-python must be set")

    if cargo_path.is_file():
        manifests = [load_toml(path) for path in cargo_manifests(root)]
        if not any(contains_text(manifest, "pyo3") for manifest in manifests):
            failures.append("Cargo manifests do not declare PyO3")
        if requires_python and not any(
            contains_text(manifest, "abi3-py") for manifest in manifests
        ):
            failures.append("PyO3 abi3 baseline is not declared in Cargo manifests")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path)
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()

    failures = check(root)
    if failures:
        print(f"NONCOMPLIANT ({len(failures)} findings)")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(
        "Conforming mechanical baseline. Review references/standard.md for semantic rules."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
