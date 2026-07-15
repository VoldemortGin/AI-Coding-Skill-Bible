#!/usr/bin/env python3
"""Check that a Gradle multi-module project conforms to java-project-standard's structural invariants.

Usage:
    python check_conformance.py [PROJECT_ROOT]   # default: current directory

A non-zero exit means violations; suitable for CI or pre-commit.
`ci.sh` (Spotless + compile -Werror + Error Prone + NullAway + test + JaCoCo) governs behavior and
quality; this script governs structure.

Gradle has no clean `dump-package`-style manifest export, so this parses build.gradle.kts /
settings.gradle.kts with text/regex -- an approximation, but enough for structural invariants.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Vendor / heavy-SDK denylist: Maven-coordinate substrings for LLM / vector-store / ML SDKs (lowercase).
# `:domain` (and any feature module) hitting one is a violation (the core abstraction is zero-SDK).
SDK_DENYLIST = frozenset({
    "openai", "anthropic", "generativeai", "google-genai", "cohere", "mistral",
    "ollama", "replicate", "groq", "langchain4j", "langchain", "dev.langchain",
    "pinecone", "qdrant", "weaviate", "chromadb", "milvus",
    "huggingface", "onnxruntime", "tensorflow", "pytorch", "deeplearning4j",
    "org.deeplearning4j", "ai.djl", "llama", "whisper",
})

# Framework denylist: `:domain` must be framework-free (a plain java-library).
DOMAIN_FRAMEWORK_TOKENS = (
    "org.springframework", "springframework", "io.micronaut", "micronaut",
    "io.quarkus", "quarkus", "com.google.dagger", "dagger", "com.google.inject",
    "jakarta.", "org.jboss",
)

# ci.sh must chain these gates (each with synonyms; any hit satisfies it).
CI_GATES = (
    ("format (Spotless)", ("spotlesscheck", "spotless")),
    ("compile (-Werror)", ("compilejava", "assemble", "build")),
    ("test", ("test",)),
    ("coverage (JaCoCo)", ("jacocotestcoverageverification", "jacoco")),
)

_INCLUDE_RE = re.compile(r'include\(\s*["\']:([\w:\-]+)["\']\s*\)')


def _discover_modules(root: Path) -> list[Path]:
    """Sub-directories with a build.gradle.kts (excluding root, build/, .gradle/) are modules."""
    mods: list[Path] = []
    for gradle in root.rglob("build.gradle.kts"):
        d = gradle.parent
        if d == root:
            continue
        parts = set(d.relative_to(root).parts)
        if "build" in parts or ".gradle" in parts:
            continue
        mods.append(d)
    return sorted(mods)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def check(root: Path) -> list[str]:
    problems: list[str] = []

    # 1. Required root files.
    required = [
        ("settings.gradle.kts", "Gradle module registration"),
        ("build.gradle.kts", "root build (shared plugins)"),
        ("gradle/libs.versions.toml", "version catalog (pinned versions)"),
        (".editorconfig", "editor + non-Java formatting rules"),
        ("ci.sh", "the one zero-warning gate"),
        ("CLAUDE.md", "root routing table"),
    ]
    for rel, why in required:
        if not (root / rel).is_file():
            problems.append(f"missing {rel} ({why}).")

    settings_text = _read(root / "settings.gradle.kts")
    catalog = _read(root / "gradle" / "libs.versions.toml")
    editorconfig = _read(root / ".editorconfig")
    ci = _read(root / "ci.sh")

    # 2. Multi-module: settings includes at least two modules.
    includes = _INCLUDE_RE.findall(settings_text)
    if len(includes) < 2:
        problems.append(
            f"settings.gradle.kts includes only {len(includes)} module(s) (need >= 2, multi-module)."
        )

    # 3. Module discovery + a CLAUDE.md per module + a test dir per non-app module.
    modules = _discover_modules(root)
    if not modules:
        problems.append("no module with a build.gradle.kts found (expected a Gradle multi-module).")
    module_names = {m.name for m in modules}
    module_builds = {m: _read(m / "build.gradle.kts") for m in modules}
    for m in modules:
        rel = m.relative_to(root)
        if not (m / "CLAUDE.md").is_file():
            problems.append(f"{rel} missing CLAUDE.md (each module needs a local contract).")
        if m.name != "app" and not (m / "src" / "test").is_dir():
            problems.append(f"{rel} has no src/test (tests are the immutable spec; every non-app module is tested).")

    # 4. :domain exists and is zero-SDK / zero-framework / does not depend on :adapters.
    domain_build_path = root / "domain" / "build.gradle.kts"
    if "domain" not in module_names or not domain_build_path.is_file():
        problems.append("missing `:domain` module (the model-agnostic core abstraction, zero SDK / zero framework).")
    else:
        text = _read(domain_build_path).lower()
        sdk_hit = sorted({s for s in SDK_DENYLIST if s in text})
        if sdk_hit:
            problems.append(f":domain depends on SDK(s) {sdk_hit}: :domain must be zero-SDK (impls go in :adapters).")
        fw_hit = sorted({t for t in DOMAIN_FRAMEWORK_TOKENS if t in text})
        if fw_hit:
            problems.append(f":domain pulls in framework token(s) {fw_hit}: :domain must be a plain java-library.")
        if 'project(":adapters")' in text or "project(':adapters')" in text:
            problems.append(":domain depends on :adapters (dependency direction must be one-way: domain <- adapters).")

    # 5. Strict compilation: -Werror configured (per module or at root).
    root_build_lower = _read(root / "build.gradle.kts").lower()
    for m in modules:
        mb = module_builds[m].lower()
        if "-werror" not in mb and "-werror" not in root_build_lower:
            problems.append(f"{m.relative_to(root)}/build.gradle.kts does not set -Werror (warnings must be fatal).")

    # 6. Error Prone + NullAway wired: present in build files, NullAway elevated to error().
    all_builds = "\n".join(module_builds.values()).lower()
    if "errorprone" not in all_builds:
        problems.append("no module wires Error Prone (net.ltgt.errorprone / options.errorprone).")
    if "nullaway" not in all_builds:
        problems.append("no module wires NullAway (net.ltgt.nullaway / options.errorprone.nullaway).")
    if "nullaway {" in all_builds and "error()" not in all_builds:
        problems.append("NullAway is present but not elevated to error() (null-safety must fail the build).")

    # 7. Spotless format gate.
    if "spotless" not in all_builds:
        problems.append("no module wires Spotless (the format gate).")
    if "googlejavaformat" not in all_builds and "palantirjavaformat" not in all_builds:
        problems.append("Spotless present but no Java formatter configured (googleJavaFormat / palantirJavaFormat).")

    # 8. JaCoCo coverage verification wired on non-app modules.
    non_app_with_verif = [
        m for m in modules
        if m.name != "app" and "jacocotestcoverageverification" in module_builds[m].lower()
    ]
    if not non_app_with_verif:
        problems.append("no non-app module wires jacocoTestCoverageVerification (coverage floor must be in the gate).")

    # 9. ci.sh: set -euo pipefail + chains the gates.
    if ci:
        if "set -euo pipefail" not in ci:
            problems.append("ci.sh missing `set -euo pipefail`.")
        low = ci.lower()
        for label, keywords in CI_GATES:
            if not any(kw in low for kw in keywords):
                problems.append(f"ci.sh does not chain the {label} gate (keywords: {' / '.join(keywords)}).")

    # 10. libs.versions.toml pins the toolchain.
    if catalog:
        low = catalog.lower()
        for tool in ("errorprone", "nullaway", "spotless", "junit"):
            if tool not in low:
                problems.append(f"libs.versions.toml does not pin {tool}.")
        if "google-java-format" not in low and "palantir" not in low:
            problems.append("libs.versions.toml does not pin a Java formatter (google-java-format / palantir).")

    # 11. Generated bindings gate-excluded (only checked when a generated dir exists).
    generated_dirs = [
        d for d in root.rglob("*")
        if d.is_dir() and d.name == "generated"
        and "build" not in d.relative_to(root).parts
        and ".gradle" not in d.relative_to(root).parts
    ]
    if generated_dirs:
        excluded = ("generated" in all_builds and "targetexclude" in all_builds) or (
            "generated" in editorconfig.lower() and "ignore" in editorconfig.lower()
        )
        if not excluded:
            rels = sorted(str(d.relative_to(root)) for d in generated_dirs)
            problems.append(
                f"found generated-bindings dir {rels} but it is not excluded from Spotless/Error Prone "
                "(polyglot-core-standard rule 4: generated bindings are gate-excluded)."
            )

    return problems


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"FAIL: path does not exist or is not a directory: {root}")
        return 2
    problems = check(root)
    if problems:
        print(f"FAIL: not conforming ({len(problems)} issue(s)):\n")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("OK: passes the key structural checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
