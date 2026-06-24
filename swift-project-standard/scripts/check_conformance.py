#!/usr/bin/env python3
"""检查一个 SwiftPM 包是否符合 swift-project-standard 的关键结构不变量。

用法:
    python check_conformance.py [PROJECT_ROOT]   # 默认当前目录

退出码非 0 表示有违规;适合放进 CI 或 pre-commit。
swift-format + swiftlint + build + test(ci.sh)那条门管行为与质量;本脚本管结构。

优先用 `swift package dump-package --package-path ROOT` 出 manifest JSON 解析(机械、可靠);
swift 不可用或失败时回退到对 Package.swift 的正则/字符串检查,并在输出里说明回退。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# 厂商 / 重型 SDK 黑名单:Swift 生态 LLM / 向量库 / ML SDK 的 **product 名**。
# Domain target 的依赖里出现任一即违规(核心抽象零 SDK;实现放 Adapters)。
# 可按需增删(团队若引入新 SDK,把它的 SwiftPM product 名加进来)。
SDK_DENYLIST = frozenset({
    # OpenAI 及兼容客户端
    "OpenAI", "SwiftOpenAI", "AsyncOpenAI", "MacPawOpenAI",
    # Anthropic
    "Anthropic", "AnthropicSwiftSDK", "SwiftAnthropic",
    # Google / 其他厂商
    "GoogleGenerativeAI", "GenerativeAI", "Cohere", "MistralAI", "Groq",
    "Replicate", "Ollama", "OllamaKit",
    # 编排框架
    "LangChain", "LangGraph",
    # 向量库 / 检索
    "Pinecone", "Qdrant", "Weaviate", "Chroma", "Milvus", "MongoDBVectorSearch",
    # 模型 / 推理 / 本地 LLM
    "HuggingFace", "Transformers", "SwiftTransformers",
    "MLX", "MLXLLM", "MLXNN", "LLM", "LlamaKit", "llama", "whisper",
})

# 大小写不敏感的黑名单(回退正则检查用)。
_DENY_LOWER = frozenset(name.lower() for name in SDK_DENYLIST)


def _dump_package(root: Path) -> dict | None:
    """跑 `swift package dump-package` 拿 manifest JSON。失败返回 None(触发回退)。"""
    try:
        proc = subprocess.run(
            ["swift", "package", "dump-package", "--package-path", str(root)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _dep_names(dep: dict) -> list[str]:
    """从一个 target dependency 节点抽出可比对的名字(byName / product / target)。"""
    names: list[str] = []
    for key in ("byName", "target"):
        if key in dep and isinstance(dep[key], list) and dep[key]:
            head = dep[key][0]
            if isinstance(head, str):
                names.append(head)
    if "product" in dep and isinstance(dep["product"], list) and dep["product"]:
        # product 形如 ["ProductName", "PackageName", ...];product 名最重要,也带上 package 名。
        for item in dep["product"][:2]:
            if isinstance(item, str):
                names.append(item)
    return names


def _target_uses_v6(target: dict) -> bool:
    for setting in target.get("settings", []):
        kind = setting.get("kind", {})
        mode = kind.get("swiftLanguageMode")
        if isinstance(mode, dict) and str(mode.get("_0")) == "6":
            return True
    return False


def _check_via_manifest(root: Path, manifest: dict) -> list[str]:
    problems: list[str] = []

    # 1. tools-version ≥ 6 + v6 语言模式。
    tools = manifest.get("toolsVersion", {}).get("_version", "0")
    try:
        major = int(str(tools).split(".")[0])
    except ValueError:
        major = 0
    if major < 6:
        problems.append(f"swift-tools-version 为 {tools},需 ≥ 6。")

    targets = manifest.get("targets", [])
    targets_by_name = {t["name"]: t for t in targets}
    non_test = [t for t in targets if t.get("type") != "test"]

    # 顶层 swiftLanguageVersions 含 v6,或每个非 test target 都用 v6 语言模式 —— 满足其一。
    top_versions = manifest.get("swiftLanguageVersions") or []
    top_has_v6 = any(str(v).startswith("6") for v in top_versions)
    if not top_has_v6:
        missing = [t["name"] for t in non_test if not _target_uses_v6(t)]
        if missing:
            problems.append(
                "未启用 Swift 6 语言模式:既无顶层 swiftLanguageVersions=[.v6],"
                f"以下 target 也未设 swiftLanguageMode(.v6):{missing}。"
            )

    # 2. Domain target 存在且零 SDK 依赖。
    domain = targets_by_name.get("Domain")
    if domain is None:
        problems.append("manifest 缺少 `Domain` target(模型无关的核心抽象)。")
    else:
        leaked: set[str] = set()
        for dep in domain.get("dependencies", []):
            for name in _dep_names(dep):
                if name in SDK_DENYLIST:
                    leaked.add(name)
        if leaked:
            problems.append(
                f"Domain target 依赖了 SDK {sorted(leaked)}:"
                "Domain 必须零 SDK,provider 实现放 Adapters。"
            )

    # 顶层 package dependencies 不应引入黑名单包(按 url 末段近似匹配)。
    for pkg_dep in manifest.get("dependencies", []):
        blob = json.dumps(pkg_dep).lower()
        hit = sorted(n for n in SDK_DENYLIST if n.lower() in blob)
        if hit:
            problems.append(
                f"顶层 package dependencies 出现疑似 SDK {hit}:"
                "默认 build 应离线零 SDK,真实后端用 trait 门控。"
            )
            break

    # 5. 每个非 test target 的目录有 CLAUDE.md。
    for t in non_test:
        # target 路径:显式 path 或默认 Sources/<name>。
        rel = t.get("path") or f"Sources/{t['name']}"
        tdir = root / rel
        if tdir.is_dir() and not (tdir / "CLAUDE.md").is_file():
            problems.append(f"{rel} 缺少 CLAUDE.md(每个 target 需就近契约)。")

    return problems


def _check_via_regex(root: Path) -> list[str]:
    """swift 不可用时的回退:对 Package.swift 文本做近似检查。"""
    problems: list[str] = ["(回退模式:swift package dump-package 不可用,改用文本近似检查)"]
    manifest_path = root / "Package.swift"
    text = manifest_path.read_text(encoding="utf-8")

    m = re.search(r"swift-tools-version:\s*([0-9]+)", text)
    if not m or int(m.group(1)) < 6:
        problems.append("Package.swift 头部 swift-tools-version 不是 ≥ 6。")
    if ".v6" not in text and "swiftLanguageMode" not in text:
        problems.append("Package.swift 未见 Swift 6 语言模式(.v6)。")

    # Domain target 块:粗略截取 `.target(name: "Domain"` 到下一个 `.target`/`.executableTarget` 之间。
    dm = re.search(r'\.target\(\s*name:\s*"Domain".*?\)', text, re.DOTALL)
    if dm is None:
        problems.append("Package.swift 未找到 `Domain` target。")
    else:
        block_lower = dm.group(0).lower()
        leaked = sorted(n for n in _DENY_LOWER if f'"{n}"' in block_lower)
        if leaked:
            problems.append(f"Domain target 块疑似依赖 SDK {leaked}(回退近似匹配)。")

    # CLAUDE.md:直接遍历 Sources/ 子目录。
    sources = root / "Sources"
    if sources.is_dir():
        for d in sorted(sources.iterdir()):
            if d.is_dir() and not (d / "CLAUDE.md").is_file():
                problems.append(f"Sources/{d.name} 缺少 CLAUDE.md。")

    return problems


def check(root: Path) -> list[str]:
    problems: list[str] = []

    # 0. 根有 Package.swift。
    if not (root / "Package.swift").is_file():
        return ["缺少根 Package.swift(不是 SwiftPM 包)。"]

    # 1/2/5:优先 manifest,失败回退。
    manifest = _dump_package(root)
    if manifest is not None:
        problems += _check_via_manifest(root, manifest)
    else:
        problems += _check_via_regex(root)

    # 3. 必备工程门禁文件。
    for f, why in [
        ("ci.sh", "唯一零警告门"),
        (".swift-format", "swift-format 配置"),
        (".swiftlint.yml", "SwiftLint 配置"),
        ("CLAUDE.md", "根级路由表"),
    ]:
        if not (root / f).is_file():
            problems.append(f"缺少 {f}({why})。")

    # 4 + 6. ci.sh 串了四道门 + warnings-as-errors。
    ci = root / "ci.sh"
    if ci.is_file():
        body = ci.read_text(encoding="utf-8")
        low = body.lower()
        if not ("swift format" in low or "swift-format" in low):
            problems.append("ci.sh 未调用 swift-format(swift format / swift-format)。")
        if "swiftlint" not in low:
            problems.append("ci.sh 未调用 swiftlint。")
        if "swift build" not in low:
            problems.append("ci.sh 未调用 swift build。")
        if "swift test" not in low:
            problems.append("ci.sh 未调用 swift test。")
        # warnings-as-errors:ci.sh 有 -warnings-as-errors,或 manifest 设了 treatAllWarnings。
        ci_wae = "-warnings-as-errors" in body
        manifest_wae = manifest is not None and "treatallwarnings" in json.dumps(manifest).lower()
        if not (ci_wae or manifest_wae):
            problems.append(
                "未启用 warnings-as-errors:ci.sh 缺 `-warnings-as-errors`,"
                "manifest 也无 treatAllWarnings。"
            )

    return problems


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    problems = check(root)
    # 回退提示行不计入违规计数,但仍打印。
    real = [p for p in problems if not p.startswith("(回退模式")]
    notes = [p for p in problems if p.startswith("(回退模式")]
    for n in notes:
        print(n)
    if real:
        print(f"✗ 不符合规范({len(real)} 项):\n")
        for p in real:
            print(f"  - {p}")
        return 1
    print("✓ 通过关键结构检查。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
