# __PROJECT__ — AI 开发约束(常驻,根级路由表)

> 只放硬约束 + 去哪找。**每个 crate 有自己的 `CLAUDE.md`**(就近契约),领域细节不在此堆叠。

## 不可违反(违反即破坏设计)
- `#![forbid(unsafe_code)]`(工作区 lint 已设);clippy 严格,门禁 `-D warnings`。编译器是主要的正确性保证。
- 边界用 serde 反序列化为强类型 + **newtype 让非法状态不可表示**;不信任外部输入符合假设。
- 外部 AI 依赖只经 `domain` 的 trait;厂商 SDK 只在 `adapters`(feature 门控);**`domain` crate 零 SDK 依赖**。
- 不静默失败:用 `Result`/`?` + `thiserror`;不滥用 `unwrap`/`expect`(逃生须 `#[allow]` + 理由)。厂商错在 adapter 归一到 `ProviderError`。
- 完成 = 一条门绿:`./ci.sh`(fmt + clippy -D warnings + doc + test + cargo-deny)。唯一判据,不许"看着没问题就提交"。
- 结构 domain-first、尽量深(workspace + crate-per-domain + 深模块);命名即定位。

## 流程
- 方向先写 `docs/adr/`(编号、不可变:背景 + 选定 + 被否决备选及理由)再编码。
- TDD:先写会失败的测试(`#[test]` / 文档测试),再实现到绿,绝不弱化测试。
- 大改拆编号步骤,每步过 `./ci.sh` 再下一步,不攒巨 diff。
- 写完另起独立、带敌意的复审(假设有错去证伪),优先审测试盖不到的图/文档/取舍。

## 去哪找
- 完整标准与 rationale:skill 的 `references/standard.md`。
- 各 crate 契约:`crates/<name>/CLAUDE.md`。
