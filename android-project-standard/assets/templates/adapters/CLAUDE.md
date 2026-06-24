# module: :adapters — 契约

职责:`:domain` interface 的具体实现 + 装配缝工厂。
- `MockProvider`(`MockLlm` / `MockEmbedder`)是**默认**实现(不是测试桩):确定性、离线、无需 key、**零 SDK**。
- `ProviderFactory` 按 config 字符串选实现:默认 `mock`,未知 provider **显式抛错**(绝不沉默回退)。`:app` 的 Hilt 组合根调用它注入。
- 真实后端(如 `OpenAIProvider`)放在 **gated 的独立 module**(如 `:adapters-openai`):
  - 在 `settings.gradle.kts` 按 gradle property 决定是否 `include(":adapters-openai")`(Cargo feature / SPM trait 的对应物);默认 build 不含,不拉 SDK。
  - adapter 内把厂商各色错误**归一到 `ProviderError`**(`Transport` / `InvalidResponse` / `MissingCredentials`);程序 bug 照常上抛。
- 默认 build/test 完全离线,绝不拉取任何第三方 SDK。
- 依赖方向:上游 `:domain` + `:kernel`;下游 `:app` 在组合根按 config 选用。**绝不**被 `:domain` / 领域 feature 依赖。
- 一致性契约:任何号称实现某 port 的类型(Mock 与真实后端)都跑 `ProviderConformanceTest` 同一组行为不变量 —— 可插拔只在行为一致时才安全。
