#!/usr/bin/env python3
"""Scaffold a new Gradle multi-module (module-per-domain) skeleton per java-project-standard.

Usage:
    python scaffold.py <base_package> [--target DIR] [--domains a b c]

Example:
    python scaffold.py com.example.notes --target ~/code/notes --domains retrieval generation

The whole tree mirrors assets/templates/ with two substitutions:
  - file CONTENT: `__PKG__` -> the dotted base package (e.g. com.example.notes).
  - directory PATH: `__PKG_PATH__` -> its `/` form (com/example/notes), i.e. the Java source-package
    directory. The two are coupled (PKG_PATH = PKG with '.' -> '/'), so you only pass one package.

Gradle has no Cargo `members=["*"]` glob -- every module must be `include`d explicitly. So this
script injects each domain feature module at two sentinels:
  - settings.gradle.kts    `// __DOMAIN_MODULES__`   -> `include(":<name>")`
  - app/build.gradle.kts   `// __DOMAIN_APP_DEPS__`  -> `implementation(project(":<name>"))`
and generates a java-library feature module per domain (depends on :domain + :kernel only).

Then: cd into the project -> `gradle wrapper --gradle-version 9.4.1` (first time) -> `./ci.sh`.
"""

from __future__ import annotations

import argparse
import re
import shutil
import stat
import subprocess
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
PKG_PLACEHOLDER = "__PKG__"
PKG_PATH_PLACEHOLDER = "__PKG_PATH__"

SENTINEL_SETTINGS = "// __DOMAIN_MODULES__"
SENTINEL_APP_DEPS = "// __DOMAIN_APP_DEPS__"

GRADLE_VERSION = "9.4.1"

# Java hard keywords (not valid as a package segment or module name).
_KEYWORDS = frozenset({
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "true", "false", "null",
    "var", "record", "yield", "sealed", "permits",
})

# Fixed built-in modules -- domain names must not collide with these.
_RESERVED_MODULES = frozenset({"app", "kernel", "domain", "adapters"})

_SEGMENT_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_DOMAIN_RE = re.compile(r"^[a-z][a-z0-9]*$")


def _valid_package(pkg: str) -> bool:
    """Valid base package: >= 2 segments, each lowercase-first then [a-z0-9_], non-keyword."""
    segments = pkg.split(".")
    if len(segments) < 2:
        return False
    return all(_SEGMENT_RE.match(s) and s not in _KEYWORDS for s in segments)


def _valid_domain(name: str) -> bool:
    """Valid domain: a legal Gradle module name AND Java package segment (lowercase, no underscore)."""
    return bool(_DOMAIN_RE.match(name)) and name not in _KEYWORDS


def _pascal(name: str) -> str:
    return name[:1].upper() + name[1:]


def _domain_build_gradle() -> str:
    return """// :__DOMAIN__ -- domain logic. Depends on :domain + :kernel, never on :adapters / an SDK.

import net.ltgt.gradle.errorprone.errorprone
import net.ltgt.gradle.nullaway.nullaway

plugins {
    `java-library`
    alias(libs.plugins.errorprone)
    alias(libs.plugins.nullaway)
    alias(libs.plugins.spotless)
    jacoco
}

nullaway {
    annotatedPackages.add("__PKG__")
}

tasks.withType<JavaCompile>().configureEach {
    options.release.set(21)
    options.compilerArgs.addAll(listOf("-Werror", "-Xlint:all,-processing,-serial", "-parameters"))
    options.errorprone {
        disableWarningsInGeneratedCode.set(true)
        excludedPaths.set(".*/generated/.*")
        nullaway {
            error()
        }
    }
}

spotless {
    java {
        googleJavaFormat(libs.versions.google.java.format.get())
        targetExclude("**/generated/**")
    }
}

tasks.named<Test>("test") {
    useJUnitPlatform()
    finalizedBy(tasks.named("jacocoTestReport"))
}

tasks.named<JacocoCoverageVerification>("jacocoTestCoverageVerification") {
    dependsOn(tasks.named("test"))
    violationRules {
        rule {
            limit {
                counter = "LINE"
                minimum = "0.80".toBigDecimal()
            }
        }
    }
}

tasks.named("check") {
    dependsOn(tasks.named("jacocoTestCoverageVerification"))
}

dependencies {
    implementation(project(":domain"))
    implementation(project(":kernel"))

    errorprone(libs.errorprone.core)
    errorprone(libs.nullaway)
    compileOnly(libs.errorprone.annotations)

    testImplementation(libs.junit.jupiter)
    testRuntimeOnly(libs.junit.platform.launcher)
}
"""


def _domain_claude_md(name: str) -> str:
    return f"""# module: :{name} — contract

Responsibility: domain logic -- {name}. Uses `:domain`'s ports + its own models / logic.
- External dependencies are used only through a constructor-injected `:domain` port (`Llm` /
  `Embedder`); **never** depend on `:adapters` or a vendor SDK -- swapping impl / model needs no
  change here.
- No silent failure: errors propagate (provider-boundary failures are normalized to
  `ProviderException` by the adapter).
- Go deep: split sub-capabilities into sub-packages / types; names resolve to paths.
- Tests are the immutable spec; coverage is in the gate (>= 80% line).
- Dependency direction: upstream `:domain` + `:kernel`; downstream `:app` (composition root) injects
  an impl and calls in.
"""


def _domain_source(pkg: str, name: str) -> str:
    pascal = _pascal(name)
    return f"""package {pkg}.{name};

import {pkg}.domain.Llm;
import {pkg}.domain.ProviderException;

/**
 * {pascal} domain logic. Injects the {{@link Llm}} port (a :domain abstraction); never touches a
 * concrete impl or SDK, so swapping impl / model needs no change here.
 */
public final class {pascal} {{
  private final Llm llm;

  public {pascal}(Llm llm) {{
    this.llm = llm;
  }}

  public String run(String query) throws ProviderException {{
    return llm.complete(query);
  }}
}}
"""


def _domain_test(pkg: str, name: str) -> str:
    pascal = _pascal(name)
    return f"""package {pkg}.{name};

import static org.junit.jupiter.api.Assertions.assertEquals;

import {pkg}.domain.Llm;
import {pkg}.domain.ProviderException;
import org.junit.jupiter.api.Test;

class {pascal}Test {{
  @Test
  void delegatesToInjectedLlm() throws ProviderException {{
    Llm stub = prompt -> "answer:" + prompt;
    assertEquals("answer:hi", new {pascal}(stub).run("hi"));
  }}
}}
"""


def _inject_settings(text: str, domains: list[str]) -> str:
    if SENTINEL_SETTINGS not in text:
        raise SystemExit(f"settings.gradle.kts template missing sentinel {SENTINEL_SETTINGS!r}.")
    includes = "\n".join(f'include(":{d}")' for d in domains)
    return text.replace(SENTINEL_SETTINGS, includes if domains else "")


def _inject_app_deps(text: str, domains: list[str]) -> str:
    if SENTINEL_APP_DEPS not in text:
        raise SystemExit(f"app/build.gradle.kts template missing sentinel {SENTINEL_APP_DEPS!r}.")
    deps = "\n    ".join(f'implementation(project(":{d}"))' for d in domains)
    return text.replace(SENTINEL_APP_DEPS, deps if domains else "")


def _make_domain_module(target: Path, pkg: str, pkg_path: str, name: str) -> None:
    mod = target / name
    main = mod / "src" / "main" / "java" / pkg_path / name
    test = mod / "src" / "test" / "java" / pkg_path / name
    main.mkdir(parents=True, exist_ok=True)
    test.mkdir(parents=True, exist_ok=True)
    (mod / "build.gradle.kts").write_text(
        _domain_build_gradle().replace("__DOMAIN__", name).replace(PKG_PLACEHOLDER, pkg),
        encoding="utf-8",
    )
    (mod / "CLAUDE.md").write_text(_domain_claude_md(name), encoding="utf-8")
    (main / f"{_pascal(name)}.java").write_text(_domain_source(pkg, name), encoding="utf-8")
    (test / f"{_pascal(name)}Test.java").write_text(_domain_test(pkg, name), encoding="utf-8")


def scaffold(pkg: str, target: Path, domains: list[str]) -> None:
    if not _valid_package(pkg):
        raise SystemExit(
            f"invalid base package (need >= 2 lowercase segments, non-keyword): {pkg!r}. "
            "e.g. com.example.notes"
        )

    seen: set[str] = set()
    for dom in domains:
        if not _valid_domain(dom):
            raise SystemExit(
                f"invalid domain name (lowercase-first, then [a-z0-9], non-keyword): {dom!r}. "
                "e.g. --domains retrieval generation"
            )
        if dom in _RESERVED_MODULES:
            raise SystemExit(f"domain name collides with a built-in module: {dom!r}. Rename it.")
        if dom in seen:
            raise SystemExit(f"duplicate domain name: {dom!r}.")
        seen.add(dom)

    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"target directory is not empty: {target}. Use an empty or new path.")

    pkg_path = pkg.replace(".", "/")

    # 1. Mirror the tree: replace __PKG__ in content, __PKG_PATH__ in paths.
    for src in TEMPLATES.rglob("*"):
        if not src.is_file():
            continue
        rel = str(src.relative_to(TEMPLATES)).replace(PKG_PATH_PLACEHOLDER, pkg_path)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8").replace(PKG_PLACEHOLDER, pkg)
        if src.name == "settings.gradle.kts":
            text = _inject_settings(text, domains)
        elif rel == str(Path("app") / "build.gradle.kts"):
            text = _inject_app_deps(text, domains)
        dst.write_text(text, encoding="utf-8")
        if src.name.endswith(".sh"):
            dst.chmod(dst.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # 2. Domain feature module skeletons (depend on :domain + :kernel only).
    for dom in domains:
        _make_domain_module(target, pkg, pkg_path, dom)

    # 3. (Optional) generate the Gradle wrapper if a system gradle is present.
    if shutil.which("gradle"):
        try:
            subprocess.run(
                ["gradle", "wrapper", "--gradle-version", GRADLE_VERSION],
                cwd=target,
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"OK: generated Gradle wrapper (gradle {GRADLE_VERSION})")
        except subprocess.CalledProcessError as exc:
            print(
                "WARN: gradle wrapper failed (run "
                f"`gradle wrapper --gradle-version {GRADLE_VERSION}` later):"
            )
            print((exc.stderr or exc.stdout or "").strip())
    else:
        print(
            "WARN: no gradle found. Install one, then run "
            f"`gradle wrapper --gradle-version {GRADLE_VERSION}` at the project root."
        )

    print(f"OK: scaffolded Gradle multi-module project: {target}")
    print(f"  base package: {pkg}")
    print(f"  domain modules: {', '.join(domains) if domains else '(none)'}")
    print("  next:")
    print(f"    cd {target}")
    print(f"    gradle wrapper --gradle-version {GRADLE_VERSION}   # if not generated above")
    print("    ./ci.sh                # spotlessCheck -> compileJava(-Werror) -> test -> coverage")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Scaffold a Gradle multi-module (module-per-domain) skeleton per java-project-standard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "base_package is the dotted Java base package / group (e.g. com.example.notes).\n"
            "domain names are Gradle module names + package segments, e.g. --domains retrieval generation"
        ),
    )
    ap.add_argument("base_package", help="dotted base package (e.g. com.example.notes)")
    ap.add_argument("--target", default=".", help="target directory (default: ./<last-segment>/)")
    ap.add_argument(
        "--domains",
        nargs="*",
        default=["retrieval", "generation"],
        metavar="DOMAIN",
        help="domain module names (default: retrieval generation). Pass `--domains` with no values for none.",
    )
    args = ap.parse_args()

    base = Path(args.target).resolve()
    target = base / args.base_package.split(".")[-1] if args.target == "." else base
    scaffold(args.base_package, target, list(args.domains))


if __name__ == "__main__":
    main()
