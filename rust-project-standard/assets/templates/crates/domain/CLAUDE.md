# crate: domain — 契约

职责:领域类型(models)+ ports(traits)+ 边界错误。**零厂商 SDK 依赖**(强制)。
- 只定义抽象与数据;具体 provider 实现在 `adapters`。
- 用 newtype / 强类型让非法状态尽量不可表示(边界校验的 Rust 版)。
- trait 保持 object-safe(可 `Box<dyn _>`)、接口尽量窄。
- 上游:仅 kernel(若需);下游:adapters 实现这里的 trait,领域逻辑 crate 依赖这里。
