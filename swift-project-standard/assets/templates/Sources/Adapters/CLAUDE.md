# target: Adapters — 契约

职责:`Domain` protocol 的具体实现。
- `MockProvider`(`MockLLM`/`MockEmbedder`)是**默认**实现(不是测试桩):确定性、离线、无需 key、**零 SDK**。
- 真实后端(如 `OpenAIProvider`)用 package trait `RealProviders` 门控:
  - 在 `Package.swift` 解开对应 `.package(...)` 依赖,并给本 target 加
    `.product(name: "...", package: "...", condition: .when(traits: ["RealProviders"]))`。
  - 新增 `OpenAIProvider.swift`,整文件用 `#if RealProviders ... #endif` 包裹。
  - 厂商各色错误**归一到 `ProviderError`**(`.transport` / `.invalidResponse` / `.missingCredentials`)。
- 默认 build/test 完全离线,绝不拉取任何第三方 SDK。
- 上游:`Domain` + `Kernel`;下游:`App` 在装配缝按 config 选用。
