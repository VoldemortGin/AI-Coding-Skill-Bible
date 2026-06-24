# module: :app — 契约

职责:`com.android.application` —— Compose UI + Hilt 组合根(composition root)。
- 唯一允许"按 config 选实现"的地方:`di/AppModule.kt` —— 用 Hilt `@Provides` 调 `:adapters` 的 `ProviderFactory`,默认 Mock,未知 provider 显式抛错(绝不沉默回退)。
- `App`(`@HiltAndroidApp`)在启动时可设 `Log.sink` 把 kernel 日志路由到 `android.util.Log`;加载 `AppConfig` → 选 provider → 注入。
- UI(Compose)只做渲染与编排;领域逻辑全在领域 feature module(注入 `:domain` 的 port)。
- 依赖方向:上游全部 module;下游无。
- 真实后端的 SDK 依赖**不**直接写在这里 —— 放 gated 的 `:adapters-openai`(见 `adapters/CLAUDE.md`)。
- 若本仓是 polyglot:手写的 FFI bridge(消费 UniFFI/JNI 生成绑定、把生成异常 re-type 成 host 值)是受治理的接缝代码;生成绑定本身 gate-excluded、never-edited。
