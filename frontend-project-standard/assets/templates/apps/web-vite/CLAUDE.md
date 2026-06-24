# app: @\_\_SCOPE\_\_/web-vite — 契约

职责:React + Vite **薄壳**(composition root)。

- 唯一允许碰框架(React)与"按 config 选实现"的地方之一:加载 `loadConfig` → 调 `makeLLM`/`makeEmbedder`(默认 Mock)→ 渲染结果。
- 浏览器安全:只 import `@__SCOPE__/kernel` 主入口(不碰 node fs);env 来自 `import.meta.env`(`VITE_` 前缀);提示词用 `?raw` import 内联(`@__SCOPE__/kernel/prompts/...md?raw`)。
- 不静默吞错:边界错误(如 `PromptError`)显式呈现到 UI。
- 保持极薄:领域 / 装配逻辑在 `packages/*`;组件 / 视觉 / 性能细节委托 `react-best-practices` / `composition-patterns` / `frontend-design` 等 skill。
- 上游:`@__SCOPE__/{kernel,domain,adapters}` + 领域包;下游:无。
