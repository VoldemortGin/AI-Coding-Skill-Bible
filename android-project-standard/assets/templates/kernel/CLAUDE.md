# module: :kernel — 契约

职责:跨切面基础设施 —— `Config`(强类型 `AppConfig` + 分层加载)、`Logging`(结构化日志 + 血缘 + 隐私纪律)、`Prompts`([AI 层] classpath 资源加载 + 严格渲染)。
- **无外部依赖、零 SDK**(只 kotlin stdlib + kotlinx.serialization)。
- `AppConfig` 必须在无 settings.json、无 env 时以默认值加载成功(离线测试依赖此)。
- 日志纪律:**payload(答案/原文/向量/用户输入)绝不传进 `Log`**;只记码值/计数/耗时。Android 行为由 `:app` 设 `Log.sink` 注入(kernel 保持平台无关)。
- 提示词严格渲染:缺变量抛 `PromptError.MissingVariable`,绝不静默留空(对应 StrictUndefined)。资源放 `src/main/resources/prompts/`,随 jar 出厂(对应 Bundle.module / include_str!)。
- 依赖方向:上游无;下游 `:adapters` / 领域 feature / `:app` 都可依赖。
