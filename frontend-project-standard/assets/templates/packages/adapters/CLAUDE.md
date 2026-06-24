# package: @\_\_SCOPE\_\_/adapters — 契约

职责:`@__SCOPE__/domain` interface 的具体实现 + 装配缝 `factory`。**唯一可碰 SDK 的包**。

- `MockProvider`(`MockLLM` / `MockEmbedder`)是**默认**实现(不是测试桩):确定性、离线、无需 key、**零 SDK**。
- `factory.ts` 的 `makeLLM` / `makeEmbedder` 按 `config.server.LLM_PROVIDER` 选实现;未知 provider 显式抛 / reject `ProviderError`,**绝不沉默回退**。
- 真实后端(如 openai)用法:
  - package.json 加 `optionalDependencies`(或 `peerDependencies`),env 放 key。
  - 在 factory 解开对应分支,用动态 `await import("openai")` 懒加载(默认 build / test 不拉 SDK)。
  - 厂商各色错误**归一到 `ProviderError`**(`.cause` 保留底层)。
- 默认 build / test 完全离线,绝不拉取任何第三方 SDK。
- 上游:`@__SCOPE__/domain` + `@__SCOPE__/kernel`(+ 真实 SDK 懒加载);下游:`apps/*` 在 composition root 调 factory。
