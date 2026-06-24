# crate: __PROJECT__ (app) — 契约

职责:二进制入口与**组装根**(composition root)。唯一按配置 new 出具体 adapter 并注入的地方。
- 读 `kernel::config::Settings` → `kernel::logging::init()` → 按 `llm_provider` 构造 provider → 跑流程。
- 业务代码不写裸厂商名;切换实现 = 改一个 env / feature。
- 依赖:kernel + domain + adapters + 领域逻辑 crates。
