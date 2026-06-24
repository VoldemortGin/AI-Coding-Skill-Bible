# __APP_ID__ — AI 开发约束(常驻,根级路由表)

> 只放硬约束 + 去哪找。**每个 module 有自己的 `CLAUDE.md`**(就近契约),领域细节不在此堆叠。

## 不可违反(违反即破坏设计)
- 编译期严格:每个 module `kotlin {}` 开 `allWarningsAsErrors = true`;库 module 开 `explicitApi()`。Kotlin 编译器的 null-safety + sealed/when 穷尽是主要正确性保证。
- 关死逃生舱:禁 `!!` 非空断言、未受检 `as` 强转、滥用 `lateinit`、平台类型泄漏、`GlobalScope`。detekt 把它们设为 error。逃生须 `@Suppress("UnsafeCallOnNullableType") // 原因`(显式、可审计、可 grep)。
- 不静默失败:用 sealed 错误层级 / `Result<T>`;vendor/网络/超时在 adapter 边界归一成领域错误;程序 bug 该抛不该吞(detekt `SwallowedException` = error)。
- 边界用 kotlinx.serialization 解码 + `@JvmInline value class` newtype 让非法状态不可表示(parse, don't validate);不信任外部输入符合假设。
- 外部 AI 依赖只经 `:domain` 的 interface;厂商 SDK 只在 `:adapters`(真实后端放 gated 的独立 module);**`:domain` 零 SDK / 零框架依赖**。
- 完成 = 一条门绿:`./ci.sh`(ktlint → detekt → compileDebugKotlin(-Werror)→ test)。唯一判据,不许"看着没问题就提交"。
- 结构 module-per-domain;命名即定位。依赖方向单向:领域 feature / `:adapters` → `:domain` + `:kernel`;`:app` → 全部。`:domain` 绝不依赖 `:adapters` / SDK。

## 与 polyglot-core-standard 的边界(若本仓是 polyglot)
- 本标准管 **Kotlin host 内部**(lint / 格式 / strict 编译 / module 结构 / provider seam / 测试)。
- **接缝**(core 单一真相 + 派生 UniFFI/JNI 绑定 vendored / tracked / `linguist-generated` / gate-excluded / never-edited + FFI 契约 typed&fallible + composed gate)归 polyglot-core-standard 管。
- 生成绑定(`**/uniffi/**`、`**/generated/**`)排除在 detekt / ktlint 源集之外;手写 bridge 是受治理的接缝代码。
- 本 module 的门接入 polyglot 的 `make check-android` 那一格。

## 流程
- 方向先写 `docs/adr/`(编号、不可变:背景 + 选定 + 被否决备选及理由)再编码。
- TDD:先写会失败的测试(JUnit / kotlin.test),再实现到绿,绝不弱化测试。
- 大改拆编号步骤,每步过 `./ci.sh` 再下一步,不攒巨 diff。
- 写完另起独立、带敌意的复审(假设有错去证伪),优先审测试盖不到的取舍。

## 去哪找
- 完整标准与 rationale:skill 的 `references/standard.md`。
- 各 module 契约:`<module>/CLAUDE.md`。
- 工具链/版本:`gradle/libs.versions.toml`(polyglot 仓还须对齐根 `versions.toml`)。
