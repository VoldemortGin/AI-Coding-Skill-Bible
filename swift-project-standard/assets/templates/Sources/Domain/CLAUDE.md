# target: Domain — 契约

职责:ports(protocols)+ models(newtype/Codable)+ 边界错误。**零厂商 SDK 依赖**(机械检查的不变量)。
- 只定义抽象与数据;具体 provider 实现在 `Adapters`。
- protocol 保持可被 `any` 存在类型擦除(方法别用 `Self`/associatedtype 阻碍 `any LLM`/`any Embedder`);`: Sendable`。
- 用 newtype / 值类型带校验 init(`init(_:) throws`)让非法状态不可表示;`Codable` 解码同样走校验。
- 错误用具体 enum:`ProviderError`(边界归一)、`DomainError`(领域校验)。
- 上游:无(保持纯净;若确需共享类型可依赖 `Kernel`,但**绝不**依赖 `Adapters`/SDK);下游:`Adapters` 实现这里的 protocol,领域 target 依赖这里。
