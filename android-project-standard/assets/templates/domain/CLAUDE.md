# module: :domain — 契约

职责:ports(interface)+ model(value class newtype)+ sealed 边界错误。**零厂商 SDK / 零框架依赖**(机械检查的不变量)。
- 只定义抽象与数据;具体 provider 实现在 `:adapters`。
- interface 保持窄(`suspend fun`,失败抛 `ProviderError`);只用 kotlin stdlib + kotlinx.serialization。
- 用 `@JvmInline value class` + 工厂 `of(...)`(`require`/抛 `DomainError`)让非法状态不可表示;解码经自定义 serializer 同样走校验(parse, don't validate)。
- 错误用 sealed 层级:`ProviderError`(边界归一)、`DomainError`(领域校验);穷尽 `when` 由编译器保证。
- 依赖方向:上游无(保持纯净);下游 `:adapters` 实现这里的 interface,领域 feature module 依赖这里。**绝不**依赖 `:adapters` / SDK / Android / Compose。
