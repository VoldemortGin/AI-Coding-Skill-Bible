# package: @\_\_SCOPE\_\_/kernel — 契约

职责:跨切面基础设施 —— `config`(Zod 校验的 env,server / client 双 schema + 分层加载)、`logging`(结构化 JSON logger + 敏感字段红化 + `logProvenance`)、`prompts`([AI 层] 随包出厂 `.md` 加载 + 严格渲染)。

- **零 UI 框架、零 SDK**(只 `zod` + node 内置)。
- `loadConfig` 必须在无 settings.json、无 env 时以默认值成功加载(离线测试依赖此);非法 env / 文件即抛 `ZodError`(parse, don't validate)。
- 日志纪律:已知敏感字段(token / key / password / secret / authorization)序列化前红化;绝不打印原始 payload;浏览器 / node 双端只用 `console`。
- 提示词严格渲染:缺变量 throw `PromptError`,绝不静默留空。node 用 `new URL(..., import.meta.url)` 定位;bundler 侧可改 `?raw` import。
- **浏览器安全分层**:主入口 `@__SCOPE__/kernel`(config / logging / `renderPrompt` / `PromptError`)不 import 任何 node 内置;依赖 node 内置的 `readSettingsFile` / `loadPrompt` / `renderNamedPrompt` 从子入口 `@__SCOPE__/kernel/node` 导出。浏览器壳只 import 主入口。
- 上游:无;下游:`adapters`、领域包、`apps/*` 都可依赖。
