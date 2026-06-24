# package: @\_\_SCOPE\_\_/domain — 契约

职责:`ports`(interface)+ `models`(Zod schema)+ 边界 `errors`。**零 SDK、零 UI 框架依赖**(机械检查的不变量:package.json 的 deps/devDeps/peerDeps 与 SDK 黑名单 + 框架黑名单交集必须为空;唯一允许的运行时依赖是 `zod`)。

- 只定义抽象与数据;具体 provider 实现在 `@__SCOPE__/adapters`。
- interface 保持窄:`LLM.complete(prompt) → Promise<string>`、`Embedder.embed(texts) → Promise<number[][]>`。
- 用 Zod schema 让非法状态不可表示(`TopK = z.number().int().min(1).max(100)`);外部数据用 `.parse()` 把关,`z.infer` 出类型。
- 错误用具体 class extends Error:`ProviderError`(边界归一)、`DomainError`(领域校验)。
- 上游:无(保持纯净;**绝不**依赖 `adapters` / SDK / `kernel`);下游:`adapters` 实现这里的 interface,领域包依赖这里。
