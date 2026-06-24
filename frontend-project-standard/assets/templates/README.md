# __SCOPE__

按 `frontend-project-standard` 搭建的前端 monorepo 骨架:TypeScript `strict` + 更严 flags、Zod 边界校验、零警告质量门(tsc + eslint + prettier + vitest + build)、关死逃生舱、框架无关核心 + 薄壳、零-SDK `domain` interface 缝 + 默认 `MockProvider`、结构化日志、Zod 校验的 env、pnpm + Turborepo package-per-domain 深结构。

## 布局

```
packages/
  kernel/      跨切面:config(Zod env)/ logging / prompts(随包出厂)。零框架、零 SDK
  domain/      ports(interface)+ models(Zod schema)+ errors。零 SDK、零框架
  adapters/    domain interface 实现。默认 MockProvider(离线、无 key、零 SDK);唯一可碰 SDK
  retrieval/   示例领域(由 scaffold 生成,不内置):向量检索,注入 Embedder
  generation/  示例领域(由 scaffold 生成,不内置):RAG 生成,注入 LLM + 严格提示词
apps/
  web-vite/    React + Vite 薄壳(composition root)
  web-next/    Next.js App Router 薄壳(composition root)
```

依赖方向:领域包 / `adapters` → `domain` + `kernel`;`apps/*` → 全部。**框架无关核心** = `packages/*` 全部零 React / 零 Next;只有 `apps/*` 有框架。

## 跑质量门(完成的唯一判据)

```bash
./ci.sh            # tsc → eslint → prettier → vitest → build(两壳)
# 或
make check
```

单项:

```bash
make typecheck     # tsc --noEmit(各包)
make lint          # eslint --max-warnings 0(类型感知)
make fmt           # prettier --write(写回)
make test          # vitest run(smoke + conformance)
make build         # vite + next 两壳 + 包构建
make dev           # 起开发服务(两壳并行)
```

前置:`pnpm install`(Node 22+,pnpm 10+)。

## 新增领域包

```bash
python scripts/scaffold.py __SCOPE__ --target . --domains pricing billing
```

pnpm `packages/*` glob 自动纳入,无需改 `pnpm-workspace.yaml`。

## 启用真实 provider

默认完全离线、零 SDK。真实后端用 `optionalDependencies` + 动态 `await import()` 懒加载,只在 `packages/adapters` 内实现,错误归一到 `ProviderError`(见 `packages/adapters/src/factory.ts` 的注释示例与 `packages/adapters/CLAUDE.md`)。
