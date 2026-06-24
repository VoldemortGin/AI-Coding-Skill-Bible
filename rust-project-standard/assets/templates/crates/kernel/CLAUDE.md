# crate: kernel — 契约

职责:跨切面基础设施。不含业务逻辑、不依赖领域 crate。
- `config`:env + 文件经 serde 反序列化为强类型(figment),`APP_` 前缀、`__` 分隔嵌套覆盖。
- `logging`:tracing;库只发事件,subscriber 由 app `init()` 一次;trace 只记码值/计数/耗时,绝不落载荷。
- `prompts`:`include_str!` 编译期嵌入 + minijinja 严格渲染(缺变量报错)。
- 上游:无;下游:被各 crate 共用。
