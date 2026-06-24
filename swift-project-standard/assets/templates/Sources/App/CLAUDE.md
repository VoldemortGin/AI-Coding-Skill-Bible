# target: App — 契约

职责:可执行 composition root(`main.swift` 顶层代码)。
- 唯一允许"按 config 选实现"的地方:装配缝 `makeLLM`/`makeEmbedder` —— 默认 Mock,未知 provider 显式报错(绝不沉默回退)。
- 加载 `AppConfig` → 选 provider → 注入领域 target → 跑一次 demo;用 `Log` 打日志(隐私插值)。
- 用 `main.swift` 顶层代码,**不要**再用 `@main`(二者冲突)。
- Xcode app 场景由 app target 充当此角色并 link `AppCore` 库(见 `project.yml`)。
- 上游:全部模块;下游:无。
