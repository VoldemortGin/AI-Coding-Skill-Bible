# __PACKAGE__ — AI 开发约束(常驻,根级路由表)

> 只放硬约束 + 去哪找。**每个 target 有自己的 `CLAUDE.md`**(就近契约),领域细节不在此堆叠。

## 不可违反(违反即破坏设计)
- Swift 6 语言模式(`swiftLanguageModes: [.v6]`)+ 严格并发 complete:编译期 data-race 安全。编译器是主要正确性保证。
- 关死逃生舱:禁 `!` 强解包 / `try!` / `as!` / `@unchecked Sendable` / 隐式解包可选。逃生须 `// swiftlint:disable:next force_unwrapping — 原因`(显式、可审计、可 grep)。
- 不静默失败:用 `throws` + 具体 `Error` enum(Swift 6 可 typed `throws(E)`);厂商错在 adapter 归一到 `ProviderError`;程序 bug 照常 `precondition`/`fatalError`。
- 边界用 `Codable` 解码 + **newtype 让非法状态不可表示**(parse, don't validate);不信任外部输入符合假设。
- 外部 AI 依赖只经 `Domain` 的 protocol;厂商 SDK 只在 `Adapters`(trait 门控);**`Domain` target 零 SDK 依赖**。
- 完成 = 一条门绿:`./ci.sh`(swift-format → swiftlint → build -warnings-as-errors → test)。唯一判据,不许"看着没问题就提交"。
- 结构 domain-first、target-per-domain;命名即定位。依赖方向:领域/`Adapters` → `Domain` + `Kernel`;`App` → 全部。

## 流程
- 方向先写 `docs/adr/`(编号、不可变:背景 + 选定 + 被否决备选及理由)再编码。
- TDD:先写会失败的测试(Swift Testing `@Test`/`#expect`),再实现到绿,绝不弱化测试。
- 大改拆编号步骤,每步过 `./ci.sh` 再下一步,不攒巨 diff。
- 写完另起独立、带敌意的复审(假设有错去证伪),优先审测试盖不到的取舍。

## 去哪找
- 完整标准与 rationale:skill 的 `references/standard.md`。
- 各 target 契约:`Sources/<Target>/CLAUDE.md`。
- 实现层怎么写:`swift-protocols` / `swift-concurrency` / `swift-error-handling` / `swift-testing` 等 skill。
