# app: @\_\_SCOPE\_\_/web-next — 契约

职责:Next.js App Router **薄壳**(composition root)。

- 唯一允许碰框架(Next/React)与"按 config 选实现"的地方之一:server component 里 `loadConfig` → `makeLLM`/`makeEmbedder`(默认 Mock)→ 渲染结果。
- server component 是 node 环境:可用 `@__SCOPE__/kernel/node` 的 `readSettingsFile` / `renderNamedPrompt`(随包出厂 `.md`)。client component 切勿 import node 子入口。
- 不静默吞错:边界错误自然冒泡到 error boundary(`error.tsx`)或显式处理。
- 保持极薄:领域 / 装配逻辑在 `packages/*`;Next 机制(server/client component、route handler、server action、streaming)委托 `nextjs-developer` / `nextjs-app-router-fundamentals` / `nextjs-server-client-components` 等 skill。
- 上游:`@__SCOPE__/{kernel,domain,adapters}` + 领域包;下游:无。
