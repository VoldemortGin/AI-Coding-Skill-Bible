#!/usr/bin/env python3
"""按 frontend-project-standard 生成一个新的 pnpm + Turborepo monorepo 骨架。

用法:
    python scaffold.py <scope> [--target DIR] [--domains a b c] [--shells vite next]

例:
    python scaffold.py acme --target ~/code/acme --domains retrieval generation agents
    python scaffold.py acme --target ~/code/acme --domains foo --shells vite

整树镜像 assets/templates/(把 `__SCOPE__` 换成 npm scope),并为每个领域在
`packages/<domain>/` 生成一个与模板 `packages/domain` 同构的最小领域包(package.json /
tsconfig.json / tsconfig.build.json / CLAUDE.md / src/index.ts + 一个 *.test.ts)。

pnpm `packages/*` glob 会自动纳入新建的领域包(像 Cargo workspace),因此 **无需修改**
pnpm-workspace.yaml 或任何 manifest。apps(web-vite / web-next)是领域无关的薄壳,不依赖
示例领域包,因此领域包也无需接进 apps。

`--shells`:默认两套壳都保留(vite + next);只给一个时删掉 apps/ 下未选的壳目录。
turbo 用 workspace glob 跑任务,删目录即可,根 package.json 无显式引用,无需额外处理。

之后:cd 进项目 → `pnpm install` → `./ci.sh`(完整零警告门)。
"""
from __future__ import annotations

import argparse
import re
import shutil
import stat
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
PLACEHOLDER = "__SCOPE__"

# 可选壳:apps/ 下的目录名。
ALL_SHELLS = {"vite": "web-vite", "next": "web-next"}

# npm scope:小写字母/数字/连字符,不能以连字符开头/结尾(用作 `@scope/...`)。
_SCOPE_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
# 领域名(npm 包名段):字母开头,其后小写字母/数字/连字符。
_DOMAIN_RE = re.compile(r"^[a-z][a-z0-9-]*$")

# 领域包不可与内置模块包重名(内置包已在模板里)。
_RESERVED_DOMAINS = frozenset({"kernel", "domain", "adapters", "root"})


def _valid_scope(name: str) -> bool:
    return bool(_SCOPE_RE.match(name))


def _valid_domain(name: str) -> bool:
    return bool(_DOMAIN_RE.match(name))


def _domain_package_json(scope: str, name: str) -> str:
    """与模板 packages/domain 同构,但作为领域包依赖 domain + kernel(workspace:*)。

    exports/main/types/files 结构、scripts 命令、devDependencies 版本均与模板逐字一致。
    """
    return f"""{{
  "name": "@{scope}/{name}",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "exports": {{
    ".": {{
      "types": "./dist/index.d.ts",
      "import": "./dist/index.js"
    }}
  }},
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "files": [
    "dist"
  ],
  "scripts": {{
    "typecheck": "tsc --noEmit",
    "lint": "eslint . --max-warnings 0",
    "test": "vitest run",
    "build": "tsc -p tsconfig.build.json"
  }},
  "dependencies": {{
    "@{scope}/domain": "workspace:*",
    "@{scope}/kernel": "workspace:*",
    "zod": "^4.1.13"
  }},
  "devDependencies": {{
    "typescript": "~5.9.3",
    "vitest": "^3.2.4"
  }}
}}
"""


def _domain_tsconfig() -> str:
    """与模板 packages/domain/tsconfig.json 逐字一致。"""
    return """{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "rootDir": "src",
    "outDir": "dist"
  },
  "include": ["src/**/*.ts"]
}
"""


def _domain_tsconfig_build() -> str:
    """与模板 packages/domain/tsconfig.build.json 逐字一致。"""
    return """{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "noEmit": false
  },
  "exclude": ["**/*.test.ts"]
}
"""


def _domain_claude_md(scope: str, name: str) -> str:
    return f"""# package: @{scope}/{name} — 契约

职责:领域逻辑 —— {name}。用 `@{scope}/domain` 的 ports + 自己的 models / 逻辑。

- 外部 AI 依赖只经注入的 `@{scope}/domain` interface(`LLM` / `Embedder`)使用,
  **绝不**依赖 `@{scope}/adapters` 或任何厂商 SDK / UI 框架 —— 换实现 / 换模型不必改本包。
- 用 Zod schema 让非法状态不可表示(`parse, don't validate`);外部数据在边界 `.parse()` 把关,`z.infer` 出类型。
- 不静默失败:错误向上抛(provider 边界失败由 adapter 归一到 `ProviderError`);不留空 `catch {{}}`,Promise 不悬空。
- 结构尽量深:子能力拆子文件 / 子类型,命名即定位。
- 上游:`@{scope}/domain` + `@{scope}/kernel`;下游:`apps/*`(composition root)注入实现并调用。
"""


def _domain_index_ts(scope: str, name: str) -> str:
    return f"""// {name}:领域逻辑。只经 `@{scope}/domain` 的 ports 调外部依赖,
// **绝不**依赖 `@{scope}/adapters` 或厂商 SDK / UI 框架。
//
// 外部 AI 依赖经构造注入的 Domain port(`LLM` / `Embedder`)使用;用 Zod 表达不变量,
// 在边界 parse;不静默失败(错误向上抛)。详见本包 CLAUDE.md。

import type {{ LLM }} from "@{scope}/domain";
import {{ TopK }} from "@{scope}/domain";
import {{ logProvenance }} from "@{scope}/kernel";

/** {name} 的一次请求参数(边界用 Zod 校验:非法即抛,而非沉默兜底)。 */
export interface {_pascal(name)}Request {{
  /** 用户查询。 */
  readonly query: string;
  /** 召回条数(`TopK`:整数 1..100;越界即 parse 失败)。 */
  readonly topK: number;
}}

/**
 * {name} 领域入口。注入 `LLM`(Domain port),不碰具体实现。
 *
 * @param llm - 注入的文本生成 port(由 composition root 提供;默认 MockProvider)。
 * @param request - 请求参数;`topK` 在边界经 `TopK.parse` 校验。
 * @returns 生成结果。
 * @throws provider 失败时由 adapter 归一到 `ProviderError`;`topK` 越界时 Zod 抛错。
 */
export async function run{_pascal(name)}(llm: LLM, request: {_pascal(name)}Request): Promise<string> {{
  const topK = TopK.parse(request.topK);
  logProvenance({{ source: "{name}", impl: "run{_pascal(name)}", version: "0.0.0", count: topK }});
  return llm.complete(request.query);
}}
"""


def _domain_test_ts(scope: str, name: str) -> str:
    return f"""// {name} 领域逻辑冒烟测试:注入一个最小确定性 LLM(不依赖 adapters),
// 验证 topK 边界校验与 happy path。

import type {{ LLM }} from "@{scope}/domain";
import {{ describe, expect, it }} from "vitest";

import {{ run{_pascal(name)} }} from "./index.js";

class StubLLM implements LLM {{
  complete(prompt: string): Promise<string> {{
    return Promise.resolve(`stub:${{prompt}}`);
  }}
}}

describe("{name}", () => {{
  it("runs with a valid topK", async () => {{
    const out = await run{_pascal(name)}(new StubLLM(), {{ query: "hello", topK: 5 }});
    expect(out).toBe("stub:hello");
  }});

  it("rejects an out-of-range topK at the boundary", async () => {{
    await expect(run{_pascal(name)}(new StubLLM(), {{ query: "x", topK: 0 }})).rejects.toThrow();
  }});
}});
"""


def _pascal(name: str) -> str:
    """领域包名(kebab-case)→ PascalCase 标识符,用作类型/函数名。"""
    return "".join(part.capitalize() for part in name.split("-") if part)


def _make_domain_package(packages_dir: Path, scope: str, name: str) -> None:
    pkg = packages_dir / name
    (pkg / "src").mkdir(parents=True, exist_ok=True)
    (pkg / "package.json").write_text(_domain_package_json(scope, name), encoding="utf-8")
    (pkg / "tsconfig.json").write_text(_domain_tsconfig(), encoding="utf-8")
    (pkg / "tsconfig.build.json").write_text(_domain_tsconfig_build(), encoding="utf-8")
    (pkg / "CLAUDE.md").write_text(_domain_claude_md(scope, name), encoding="utf-8")
    (pkg / "src" / "index.ts").write_text(_domain_index_ts(scope, name), encoding="utf-8")
    (pkg / "src" / f"{name}.test.ts").write_text(_domain_test_ts(scope, name), encoding="utf-8")


def scaffold(scope: str, target: Path, domains: list[str], shells: list[str]) -> None:
    if not _valid_scope(scope):
        raise SystemExit(
            f"scope 非法(npm scope:小写字母/数字/连字符,不以连字符开头或结尾):{scope!r}"
        )

    seen: set[str] = set()
    for dom in domains:
        if not _valid_domain(dom):
            raise SystemExit(
                f"领域名非法(小写包名段:字母开头,其后小写字母/数字/连字符):{dom!r}。"
                "示例:--domains retrieval generation"
            )
        if dom in _RESERVED_DOMAINS:
            raise SystemExit(f"领域名与内置包冲突:{dom!r}。请换名。")
        if dom in seen:
            raise SystemExit(f"领域名重复:{dom!r}。")
        seen.add(dom)

    selected_shells = list(dict.fromkeys(shells))
    for sh in selected_shells:
        if sh not in ALL_SHELLS:
            raise SystemExit(f"未知壳:{sh!r}。可选:{', '.join(ALL_SHELLS)}。")
    if not selected_shells:
        raise SystemExit("至少需保留一个壳(--shells vite 和/或 next)。")

    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"目标目录非空:{target}。请换一个空目录或不存在的路径。")

    # 1. 整树镜像 + 占位替换(替换文件内容里的 __SCOPE__)。
    for src in TEMPLATES.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(TEMPLATES)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8").replace(PLACEHOLDER, scope)
        dst.write_text(text, encoding="utf-8")
        if src.name.endswith(".sh"):
            dst.chmod(dst.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # 2. 删掉未选的壳目录(pnpm/turbo 用 glob 跑 workspace,删目录即可)。
    for key, dirname in ALL_SHELLS.items():
        if key not in selected_shells:
            shell_dir = target / "apps" / dirname
            if shell_dir.is_dir():
                shutil.rmtree(shell_dir)

    # 3. 领域包骨架(与模板 packages/domain 同构;pnpm glob 自动纳入)。
    for dom in domains:
        _make_domain_package(target / "packages", scope, dom)

    print(f"✓ 已生成 monorepo:{target}")
    print(f"  scope:@{scope}")
    print(f"  领域包:{', '.join(domains) if domains else '(无)'}")
    print(f"  壳:{', '.join(ALL_SHELLS[s] for s in selected_shells)}")
    print("  下一步:")
    print(f"    cd {target}")
    print("    pnpm install           # 首次拉依赖(允许联网)")
    print("    ./ci.sh                # 完整零警告门(tsc + eslint + prettier + vitest + build)")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="按 frontend-project-standard 生成 pnpm + Turborepo monorepo 骨架。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "scope 用作 npm scope(`@scope/...`);领域名用作 npm 包名段(`@scope/<domain>`)。\n"
            "约定用 kebab-case 小写,如:--domains retrieval generation agents"
        ),
    )
    ap.add_argument("scope", help="npm scope(小写字母/数字/连字符),如 acme")
    ap.add_argument("--target", default=".", help="目标目录(默认:当前目录下 <scope>/)")
    ap.add_argument(
        "--domains",
        nargs="*",
        default=["retrieval", "generation"],
        metavar="DOMAIN",
        help="领域包名(默认:retrieval generation)。传 `--domains` 不带值则不生成领域包。",
    )
    ap.add_argument(
        "--shells",
        nargs="*",
        default=["vite", "next"],
        choices=sorted(ALL_SHELLS),
        metavar="SHELL",
        help="保留的 app 壳(默认两套:vite next)。",
    )
    args = ap.parse_args()

    base = Path(args.target).resolve()
    target = base / args.scope if args.target == "." else base
    scaffold(args.scope, target, list(args.domains), list(args.shells))


if __name__ == "__main__":
    main()
