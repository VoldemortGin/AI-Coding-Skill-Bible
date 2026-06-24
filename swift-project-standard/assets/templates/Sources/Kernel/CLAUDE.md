# target: Kernel — 契约

职责:跨切面基础设施 —— `Config`(强类型 `AppConfig` + 分层加载)、`Logging`(`os.Logger` + 隐私插值 + 血缘)、`Prompts`([AI 层] `Bundle.module` 加载 + 严格渲染)。
- **无外部依赖、零 SDK**(只 Foundation/os)。声明 `resources:` 以生成 `Bundle.module`。
- `AppConfig` 必须在无 settings.json、无 env 时以默认值加载成功(离线测试依赖此)。
- 日志纪律:payload `.private`,码值/计数/耗时 `.public`;`#if canImport(os)` 回退 stderr。
- 提示词严格渲染:缺变量 throw `PromptError.missingVariable`,绝不静默留空。
- 上游:无;下游:`Adapters`、领域 target、`App` 都可依赖。
