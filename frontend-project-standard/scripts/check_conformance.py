#!/usr/bin/env python3
"""检查一个 monorepo 是否符合 frontend-project-standard 的关键结构不变量。

用法:
    python check_conformance.py [PROJECT_ROOT]   # 默认当前目录

退出码非 0 表示有违规;输出机器可读,适合放进 CI 或 pre-commit。
`ci.sh`(tsc + eslint + prettier + vitest + build)那条门管行为与质量;本脚本管结构。

package.json 是纯 JSON,直接 `json.loads`。tsconfig 可能含注释(JSONC)→ 优先用
`npx tsc --showConfig`(在 root 跑)拿展开后的有效配置;失败时回退:剥注释后 `json.loads`。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# —— SDK 黑名单(可编辑 frozenset)——
# 前端生态 LLM / 向量库 / ML SDK 的 **npm 包名**。domain 包的依赖里出现任一即违规
# (核心抽象零 SDK;实现放 adapters)。团队若引入新 SDK,把它的 npm 包名加进来。
SDK_DENYLIST = frozenset({
    # OpenAI 及编排
    "openai",
    "ai",  # Vercel AI SDK
    # Anthropic / Google / 其他厂商
    "@anthropic-ai/sdk",
    "@google/generative-ai",
    "@google/genai",
    "cohere-ai",
    "@mistralai/mistralai",
    "groq-sdk",
    "replicate",
    "ollama",
    # 编排框架
    "langchain",
    "@langchain/core",
    "@langchain/openai",
    "llamaindex",
    # 向量库 / 检索
    "@pinecone-database/pinecone",
    "@qdrant/js-client-rest",
    "weaviate-ts-client",
    "chromadb",
    # 模型 / 推理 / 本地
    "@huggingface/inference",
    "@xenova/transformers",
    "@aws-sdk/client-bedrock-runtime",
})

# —— UI 框架黑名单(可编辑 frozenset)——
# domain(及任何框架无关核心包)不得依赖 UI 框架;只有 apps/* 可碰。
FRAMEWORK_DENYLIST = frozenset({
    "react",
    "react-dom",
    "next",
    "vue",
    "svelte",
    "@angular/core",
    "solid-js",
})

# tsconfig.base.json 必须含的更严 flag(strict 之外)。
REQUIRED_STRICT_FLAGS = ("noUncheckedIndexedAccess", "exactOptionalPropertyTypes")

# eslint 配置必须含的关键禁逃生舱规则(grep 子串)。
REQUIRED_ESLINT_RULES = ("no-explicit-any", "no-non-null-assertion")

# ci.sh 必须串起的门(每项给若干同义关键词,命中其一即满足)。
CI_GATES = (
    ("typecheck", ("typecheck", "tsc")),
    ("lint", ("lint", "eslint")),
    ("format", ("format", "prettier")),
    ("test", ("test", "vitest")),
    ("build", ("build",)),
)


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _strip_jsonc(text: str) -> str:
    """剥除 // 行注释与 /* */ 块注释(容错解析 JSONC 用)。不处理字符串内的伪注释,
    但对 tsconfig 这类配置足够。"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"(^|\s)//[^\n]*", r"\1", text)
    # 去掉对象 / 数组里的尾随逗号。
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text


def _tsconfig_options(root: Path) -> dict | None:
    """拿 tsconfig.base.json 的 compilerOptions:优先 `npx tsc --showConfig`(展开后),
    失败回退剥注释后 json.loads(原始文件)。"""
    base = root / "tsconfig.base.json"
    if not base.is_file():
        return None
    # 优先 tsc --showConfig(在 root 跑,展开 extends / 注释)。
    try:
        proc = subprocess.run(
            ["npx", "--yes", "tsc", "--showConfig", "-p", "tsconfig.base.json"],
            cwd=str(root),
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(proc.stdout)
        opts = data.get("compilerOptions")
        if isinstance(opts, dict):
            return opts
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
        pass
    # 回退:剥注释后解析原始文件。
    try:
        raw = _strip_jsonc(base.read_text(encoding="utf-8"))
        data = json.loads(raw)
        opts = data.get("compilerOptions")
        return opts if isinstance(opts, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _all_deps(pkg: dict) -> set[str]:
    keys: set[str] = set()
    for field in ("dependencies", "devDependencies", "peerDependencies"):
        section = pkg.get(field)
        if isinstance(section, dict):
            keys.update(section.keys())
    return keys


def _subdirs_with_package_json(parent: Path) -> list[Path]:
    if not parent.is_dir():
        return []
    return sorted(d for d in parent.iterdir() if d.is_dir() and (d / "package.json").is_file())


def check(root: Path) -> list[str]:
    problems: list[str] = []

    # 1. 根工程文件存在。
    for f, why in [
        ("package.json", "根 workspace manifest"),
        ("pnpm-workspace.yaml", "pnpm workspace 定义"),
        ("turbo.json", "Turborepo pipeline"),
    ]:
        if not (root / f).is_file():
            problems.append(f"缺少 {f}({why})。")

    # 2. tsconfig.base.json:strict===true + 若干更严 flag。
    opts = _tsconfig_options(root)
    if opts is None:
        problems.append("无法读取 tsconfig.base.json 的 compilerOptions(文件缺失或无法解析)。")
    else:
        if opts.get("strict") is not True:
            problems.append("tsconfig.base.json 的 compilerOptions.strict 不是 true。")
        for flag in REQUIRED_STRICT_FLAGS:
            if opts.get(flag) is not True:
                problems.append(f"tsconfig.base.json 缺少更严 flag `{flag}: true`。")

    # 3. domain 包零 SDK 零框架。
    domain_pkg_path = root / "packages" / "domain" / "package.json"
    if not domain_pkg_path.is_file():
        problems.append("缺少 packages/domain/package.json(模型无关的核心抽象包)。")
    else:
        domain_pkg = _load_json(domain_pkg_path)
        if domain_pkg is None:
            problems.append("无法解析 packages/domain/package.json。")
        else:
            deps = _all_deps(domain_pkg)
            sdk_hit = sorted(deps & SDK_DENYLIST)
            fw_hit = sorted(deps & FRAMEWORK_DENYLIST)
            if sdk_hit:
                problems.append(
                    f"domain 依赖了 SDK {sdk_hit}:domain 必须零 SDK,provider 实现放 adapters。"
                )
            if fw_hit:
                problems.append(
                    f"domain 依赖了 UI 框架 {fw_hit}:domain 必须零框架,框架只在 apps/*。"
                )

    # 4. eslint 配置存在且含禁逃生舱关键规则。
    eslint_path = None
    for cand in ("eslint.config.mjs", "eslint.config.js", "eslint.config.ts", "eslint.config.cjs"):
        if (root / cand).is_file():
            eslint_path = root / cand
            break
    if eslint_path is None:
        problems.append("缺少 eslint.config.{mjs,js,ts,cjs}(类型感知 lint 配置)。")
    else:
        body = eslint_path.read_text(encoding="utf-8")
        for rule in REQUIRED_ESLINT_RULES:
            if rule not in body:
                problems.append(f"{eslint_path.name} 未见关键规则 `{rule}`(禁逃生舱)。")

    # 5. ci.sh 存在且串了五道门。
    ci = root / "ci.sh"
    if not ci.is_file():
        problems.append("缺少 ci.sh(唯一零警告门)。")
    else:
        low = ci.read_text(encoding="utf-8").lower()
        for label, keywords in CI_GATES:
            if not any(kw in low for kw in keywords):
                problems.append(
                    f"ci.sh 未串起 {label} 门(未见关键词:{' / '.join(keywords)})。"
                )

    # 6. root + 每个 packages/* 与 apps/*(有 package.json 的)有 CLAUDE.md。
    if not (root / "CLAUDE.md").is_file():
        problems.append("缺少根 CLAUDE.md(根级路由表)。")
    for parent in ("packages", "apps"):
        for d in _subdirs_with_package_json(root / parent):
            if not (d / "CLAUDE.md").is_file():
                rel = d.relative_to(root)
                problems.append(f"{rel} 缺少 CLAUDE.md(每个 package / app 需就近契约)。")

    # 7. .env.example 存在。
    if not (root / ".env.example").is_file():
        problems.append("缺少 .env.example(Zod 校验 env 的契约清单)。")

    return problems


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"✗ 路径不存在或不是目录:{root}")
        return 2
    problems = check(root)
    if problems:
        print(f"✗ 不符合规范({len(problems)} 项):\n")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("✓ 通过关键结构检查。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
