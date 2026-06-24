# Rust 项目标准(完整版)

面向 AI 主导开发的 Rust 工程标准。与 Python 姊妹标准同一条脊:**信任放在可被机器检验的代码上,而非模型。** 区别在于:Rust 的静态保证大半由编译器免费提供(类型、所有权、穷尽性,编译期强制、无类型擦除),所以**不需要外挂运行时类型检查**;本标准的重点是把少数逃生舱关上、把每个外部依赖推到 trait 后面、结构尽量深且命名即定位、并把人类的隐性兜底外化成会失败的工件。

**适用范围(分两层)**:下列约束分为**通用脊**与**AI 触发层**。通用脊——`forbid` unsafe、零警告门、`Result`/`thiserror`、serde+newtype、workspace+深命名、`cargo-deny`、`tracing`、`figment`——适用于任何 Rust 项目,与是否碰 AI 无关。AI 触发层——`domain` trait 缝、`MockProvider` 默认、`minijinja`/`include_str!` 提示词、`log_provenance`、约束下沉控制流——只在项目真的调用 LLM/embedding/向量库时启用。不碰模型的系统/库/CLI 应全量采用通用脊、整层跳过 AI 层;在那种项目里硬套 `MockProvider` 或提示词嵌入是 cargo-cult,不是合规。

基线:edition 2024、钉死工具链、`#![forbid(unsafe_code)]`、严格 clippy(workspace lints)、`serde`、`thiserror`/`anyhow`、`tracing`、`figment`、`minijinja`、`cargo-deny`。

---

## 1. 唯一的零警告门(完成的唯一判据)

`ci.sh` 一条 `set -euo pipefail` 脚本,人和 agent 共用:

```bash
cargo fmt --all -- --check
cargo clippy --all-targets --all-features -- -D warnings   # 警告即错误
RUSTDOCFLAGS="-D warnings" cargo doc --no-deps --all-features
cargo test --all-features                                  # 单测 + 文档测试 + 冒烟
cargo deny check                                           # license / 安全 / 依赖
```

任一项非零即没完成。`-D warnings` 是关键:lint 在 `[workspace.lints]` 里声明为 `warn`,门禁把它们一律提升为 error。用 pre-push hook 钉死;CI 用 `.github/workflows/ci.yml`(`dtolnay/rust-toolchain` + `Swatinem/rust-cache` + `cargo-deny-action`)镜像同一套。`./ci.sh` 需要 `cargo install cargo-deny`(CI 用 action 免装)。

## 2. 静态保证:编译器 + lint,逃生舱关死

不需要 mypy/beartype 那种外挂——Rust 类型在编译期强制。它的"最严、无逃生舱"用原生方式表达,集中在工作区:

```toml
[workspace.lints.rust]
unsafe_code = "forbid"          # 硬禁:#[allow] 也无法覆盖 forbid

[workspace.lints.clippy]
all = { level = "warn", priority = -1 }
unwrap_used = "warn"
expect_used = "warn"
panic = "warn"
# 想更严:pedantic / nursery(噪声大、需逐 lint 调,故默认不开)
```

各 crate `[lints] workspace = true` 继承。要点:

- `forbid` 比 `deny` 更强——`deny` 可被局部 `#[allow]` 关掉,`forbid` 不行。`unsafe` 用 `forbid`,这是"无逃生舱"的字面实现。
- **确需 `unsafe` 的受控出口**:个别 crate 真要 unsafe(FFI、SIMD、包 C 库)时不在工作区松绑——根 `forbid` 不动,把 unsafe **隔离进一个最小专用 crate**:该 crate **不写 `[lints] workspace = true`**(forbid 靠继承生效,不继承即不受其约束),改为自声明 `[lints.rust] unsafe_code = "deny"`(`deny` 可被逐处 `#[allow(unsafe_code)] // SAFETY: …` 局部豁免),并按需重声明严格 clippy。每处 unsafe 配 `// SAFETY:`、在该 crate 的 CLAUDE.md 记下为何需要(够大上 ADR)。引入 unsafe 由此成为一次显式、隔离、可审计、可 grep 的决策;工作区其余仍零 unsafe,`check_conformance` 仍绿(它只看根 forbid)。
- lint 声明为 `warn` + 门禁 `-D warnings`:好处是本地编译不被打断(警告可见但不挡路),只有过门那一刻警告才变致命。
- `pedantic` 信号噪声比高,多数项目从中精选而非全开;默认不开,作为可选收紧项,且需逐 lint 配 `#[allow]` 调顺。
- 工具链用 `rust-toolchain.toml` 钉死(`channel = "1.85"` + rustfmt/clippy 组件),保证人和 CI 同一把尺。

## 3. 不静默失败:`Result` + `thiserror`,而非到处 `unwrap`

- 可恢复错误用 `Result<T, E>`;库 crate 用 `thiserror` 定义具体错误枚举,二进制 crate(`app`)用 `anyhow` 聚合并加 `.context(...)`。
- `unwrap_used`/`expect_used`/`panic` 设为 clippy-warn(→ 门禁 error)。**逃生须 `#[allow(clippy::unwrap_used)]` 加一行理由注释**——这是 Python `# type: ignore[code] # 原因` 的 Rust 等价物:不是禁止,是让每次逃生显式、可审计、可 grep。
- 测试里 `unwrap`/`expect`/`panic` 默认允许(`clippy.toml` 的 `allow-unwrap-in-tests = true` 等),src 里仍禁——测试断言用 `unwrap` 是惯例。
- 厂商/网络/超时/API 错在 **adapter 边界**归一到 `domain::ProviderError`;程序 bug(逻辑错、违反不变量)照常 panic 或上抛,**绝不**塞进降级路径吞掉。这与 Python 标准的"程序错照常上抛、外部错归一"一致。

## 4. 边界:parse, don't validate —— `serde` + newtype

每个跨边界的值(配置、LLM 输出、工具结果、文件、反序列化)在入口处用 `serde` 反序列化成强类型结构;**把约束编码进类型,让非法状态不可表示**,而非运行时 if 校验:

```rust
use serde::Deserialize;

/// newtype:构造时即保证 1..=100,之后类型本身就是"已校验"的证明。
#[derive(Debug, Clone, Copy, Deserialize)]
#[serde(try_from = "u8")]
pub struct TopK(u8);

impl TryFrom<u8> for TopK {
    type Error = String;
    fn try_from(v: u8) -> Result<Self, Self::Error> {
        (1..=100).contains(&v).then_some(Self(v)).ok_or_else(|| format!("top_k 越界: {v}"))
    }
}
```

这是 Python 用 pydantic 在边界校验的 Rust 对应:pydantic 在运行时校验并强转,Rust 用 `serde` + newtype 把"已校验"变成编译期可携带的类型证明,下游函数签名收 `TopK` 就不必再防御性检查。

## 5. 配置:`figment` 分层,强类型

`kernel::config`:默认 < `configs/settings.toml` < 环境变量(`APP_` 前缀,`__` 分隔嵌套),经 `serde` 落成强类型 `Settings`。

```rust
Figment::new()
    .merge(Toml::file("configs/settings.toml"))
    .merge(Env::prefixed("APP_").split("__"))
    .extract()
```

`APP_RETRIEVER__TOP_K=20` 覆盖 `settings.retriever.top_k`。这是 pydantic-settings 的 Rust 对应(分层来源 + env 覆盖 + 强类型)。非法配置在 `Settings::load()` 即报错,不拖到运行期。

## 6. 日志/血缘:`tracing`,载荷不落盘

`kernel::logging`:

- 库 crate 只用 `tracing` 宏发事件(`tracing::info!(...)`);**绝不**在库里装 subscriber。`init()` 由 `app` 入口调用一次(`tracing_subscriber::fmt().with_env_filter(...)`,读 `RUST_LOG`)。
- **血缘**:每条 AI 产物带来源 + 产出它的实现/版本号——`log_provenance(source, impl, version, count)`,用 tracing 结构化字段记录;多实现可并存可审计。
- **隐私**:trace 只记码值/计数/耗时,**绝不**落答案/原文/向量值。把这条写进 crate 的 CLAUDE.md 当硬纪律。

## 7. 提示词:`include_str!` 编译期嵌入 + `minijinja` 严格渲染

提示词放 `kernel/src/prompts/rag/*.md`,用 `include_str!` 在**编译期**嵌进二进制——比 Python 的运行时 `importlib.resources` 更进一步:随二进制出厂,无任何运行时路径/打包问题。

```rust
pub const ANSWER: &str = include_str!("prompts/rag/answer.md");

pub fn strict_env() -> Environment<'static> {
    let mut env = Environment::new();
    env.set_undefined_behavior(UndefinedBehavior::Strict);  // 缺变量报错,而非静默空串
    env
}
```

`minijinja` 是 Jinja2 的 Rust 同源实现,`UndefinedBehavior::Strict` 对应 `StrictUndefined`。调用方 `add_template` + `render` 用 `?` 传播错误,不 `unwrap`/`expect`(以过门)。

## 8. 结构:深 Cargo workspace,crate-per-domain

深度来自**工作区**(多 crate),不是一个 crate 里堆深模块。"修 reranker"应定位到 `crates/retrieval/src/reranking/`,无需搜索。

```
repo/
├── Cargo.toml                # [workspace] members = ["crates/*", "app"]
├── rust-toolchain.toml  rustfmt.toml  clippy.toml  deny.toml
├── ci.sh  justfile  .github/workflows/ci.yml
├── CLAUDE.md                 # 根级路由表
├── docs/adr/
├── configs/settings.toml
├── crates/
│   ├── kernel/               # 跨切面:config / logging / prompts(+ CLAUDE.md)
│   ├── domain/               # ports(traits)+ models + errors,零 SDK(+ CLAUDE.md)
│   ├── adapters/             # trait 实现;唯一碰 SDK,feature 门控(+ CLAUDE.md)
│   ├── ingestion/  retrieval/  generation/  agents/   # 领域 crate(+ 各自 CLAUDE.md)
│   └── pipelines/            # 组装领域逻辑
└── app/                      # 二进制 + 组装根(+ CLAUDE.md)
```

要点:

- **crate 命名避开 std**:基础设施 crate 叫 `kernel` 不叫 `core`(`core` 与 `std::core` 冲突)。`domain`/`adapters`/`kernel` 等名字与项目名无关,故 `use kernel::config::Settings` 这类路径**不依赖项目名**——只有 workspace 根、`app/Cargo.toml` 的二进制名、CLAUDE.md 标题用到项目名。
- **依赖方向**:领域 crate → `domain`(ports)+ `kernel`,**不**依赖 `adapters` 或 SDK;`adapters` → `domain`(实现其 trait);`app` → 全部(组装根)。
- **依赖注入在组装根**:`app/src/main.rs` 按 `settings.llm_provider` `match` 出具体 adapter,`Box<dyn Llm>` 注入下游。这是 Rust 惯用的 DI(构造在边缘、trait 对象向下传),对应 Python 的 `ports/factory.py`。
- `[workspace.dependencies]` 统一版本,各 crate `dep.workspace = true`,避免版本漂移(`cargo-deny` 的 `multiple-versions` 再兜一道)。

### 8.1 每个 crate 一个 CLAUDE.md(分层上下文)

把"分层上下文"落到目录:根 `CLAUDE.md` 是**路由表**(只放硬约束 + 去哪找),每个 crate 的 `CLAUDE.md` 写本 crate 的职责、依赖方向、本地契约(如 domain 的"零 SDK"、adapters 的"错误归一"、kernel 的"载荷不落盘")。`check_conformance.py` 要求每个 crate 都有。好处:agent 进到某 crate 工作时,就近拿到的是这一层的精确约束,而非读一份大文档被噪声稀释。

### 8.2 可导航性

命名即路径,是导航层面的"类型即接口契约";workspace 把它提到 crate 级。按能力分(不按 `types/`/`utils/` 分),一直拆到叶子模块只剩单一职责。深结构 + 一致的命名,让"哪段代码在哪"无需搜索。

## 9. 模型无关:trait 缝 + 零 SDK 的 domain

模型是可热插拔的商品。把正确性、可测性、可审计性从具体模型里抽出来,钉在 trait 与确定性代码上。

- **每个外部依赖 = `domain` 里一个最小 trait**(`Llm`/`Embedder`/`Reranker`/向量库/解析器)。领域逻辑只依赖 trait;trait 保持 **object-safe**(无泛型方法、无 `Self` 返回),以便 `Box<dyn _>`。
- **`domain` crate 零厂商 SDK 依赖**:这是机械可查的不变量——`check_conformance.py` 解析 `crates/domain/Cargo.toml` 的 `[dependencies]`,与 SDK 黑名单取交集即报错。比 Python grep import 更干净:Cargo 让依赖按 crate 显式声明,黑名单只需匹配 crate 名。
- **SDK 只在 `adapters`,且 `optional` + feature 门控**:`async-openai = { version = "...", optional = true }` + `[features] openai = ["dep:async-openai"]`。这是 Python"厂商包进可选 extras + lazy import"的 Rust 对应(feature 把未选的后端整段排除出编译)。
- **厂商错归一**:adapter 内 `map_err` 把 SDK 错误转成 `domain::ProviderError`;程序错照常上抛。
- **MockProvider 作默认**(不是测试桩):`MockLlm`/`MockEmbedder`/`MockReranker` 确定性、离线、无需 key。二进制、测试、CI 默认走 mock,跑得快、稳、免费、不被随机性污染。"无 key 也能 demo/test 跑绿"设成硬验收。
- **一致性契约(conformance kit)**:任何号称实现了某 trait 的类型(Mock 与真实后端)都跑同一组行为不变量——可插拔只在所有实现行为一致时才安全。Rust 里用泛型测试函数对多实现复用:

```rust
fn assert_embedder_contract<E: Embedder>(e: &E) {
    let texts = vec!["a".to_owned(), "b".to_owned()];
    assert_eq!(e.embed(&texts).unwrap(), e.embed(&texts).unwrap()); // 确定性
    assert_eq!(e.embed(&texts).unwrap().len(), 2);                  // 数量保持
}
// #[test] fn mock_obeys_contract() { assert_embedder_contract(&MockEmbedder); }
// 真实后端在装了 SDK / 有 key 的 feature 下加一个 #[test] 复用同一函数。
```

## 10. 让 AI 输出可信:约束下沉控制流,而非写进 Prompt

Prompt 是软约束,温度/越狱/长上下文都能绕过;只有沉到代码的约束才从"概率性遵守"变成"结构上不可能违反"。

- **Constrain, don't ask**:对不可妥协属性(不编造、必引用、不越权),让模型物理上无法违反——命中事实时答案由代码从结构化值确定性合成、模型散文整段丢弃;无事实时编排层改写成"查不到"。迁移:列"绝不能发生"清单,逐条问"模型能否在听话的同时仍违反它",凡"能"的就移出模型。
- **收窄发射面**:不让模型自由生成关键载荷——让它从一个**typed `enum`** 里选、或调返回三态(found/not_found/unrecognized)的工具,最终值取自工具结果而非模型文本。Rust 的 `enum` 天然就是受控发射面。
- **安全门确定性、独立、永不可插拔**:理解类(意图解析)可替换;安全决策(越权/敏感隔离)做成确定性代码,从原始输入独立重判,不信任可插拔组件的输出。可替换的是智能,不是护栏。
- **血缘进、隐私出**:见 §6。

## 11. 把隐性兜底外化成会失败的工件

人靠经验、记忆判断"做完没""文档过时没";agent 没有这些,只优化能观测到的反馈。每加一个会失败的检查,就把一份隐性知识变成硬约束。

- **加宽的零警告门**(§1):fmt + clippy `-D warnings` + doc(`-D warnings`)+ test + `cargo-deny`。`cargo doc -D warnings` 把文档断链等变红——文档也进门禁。
- **`cargo-deny` 当真实性/合规保险丝**:license 白名单拒 AGPL/GPL/SSPL 泄入、RUSTSEC 安全公告、依赖去重。贴企业合规(SCA)那条线。
- **漂移守卫**:描述代码的 markdown 带 `covers:` 元数据,被覆盖路径失效即红(可移植 Python 标准里的 `check_drift.py`,或用 `cargo doc` 的链接检查 + 文档测试覆盖"文档里的代码示例必须真能编译运行")。Rust 的**文档测试**本身就是一种强力的反漂移:`///` 里的示例会被 `cargo test` 编译运行,文档骗不了人。
- **自描述工件从真实代码派生**:架构/依赖图从 `cargo metadata` / `cargo-modules` 内省派生,而非手画;手维护的图必然腐烂,腐烂的图比没有更危险。
- **分层上下文**(§8.1):根路由表 + 每 crate 就近契约,而非一份大文档读到底。

## 12. 驾驭 AI 做大工作:可拆分、可逐步验证、可对抗审查

把 AI 当可监督的劳力,而非无监督自动驾驶。这是工作流层(可作另一个姊妹技能),轻量版规则:

- **先决策再编码(ADR,`docs/adr/`)**:架构/产品决策写成编号、不可变的 ADR(背景 + 选定 + 被否决备选及理由)。AI 最擅长明确约束下填实现,最不可靠的是替你做含糊取舍;否决理由还防它重走已排除的路。
- **TDD 红灯先行,测试即不可动摇的规格**:每个改动先写会失败的 `#[test]` / 文档测试,再实现到绿,**绝不**为通过而弱化测试;给 subagent 的任务直接附失败测试当验收。
- **拆成编号步骤、每步独立绿灯**:大重构拆有序步骤,每步一次提交、跑完整门禁再进入下一步,绝不攒巨型 diff——把失败爆炸半径压到一步之内。
- **分解→并行→综合**:主 agent 拆边界清晰、规格完整的子任务并行分派,逐个审 diff 并在提交前过门。
- **对抗式独立复审**:写完后另起独立、带敌意的多视角复审("假设它有错,去证伪"),优先审测试盖不到的产物(图、文档、取舍)——同一 agent 既写又夸会系统性确认偏差。

---

## 附:Python 姊妹标准的映射速查

| 关注点 | Python 标准 | Rust 标准 |
|---|---|---|
| 静态类型 | mypy `--strict` | 编译器(免费) |
| 运行时类型 | beartype + claw hook | 不需要(无类型擦除) |
| "无逃生舱" | 禁裸 `Any` | `#![forbid(unsafe_code)]` |
| 不静默失败 | 无裸 `except`、StrictUndefined | `Result`/`thiserror`、clippy 限 `unwrap` |
| 边界校验 | pydantic | `serde` + newtype(parse don't validate) |
| 逃生须记录 | `# type: ignore[code] # 原因` | `#[allow(clippy::...)] // 原因` |
| 结构 | src 布局 + 包内 domain-first 深目录 | Cargo workspace + crate-per-domain |
| 模型无关 | `ports/`+`adapters/`,核心零 SDK import | `domain`(trait)+`adapters`,domain 零 SDK 依赖 |
| 可选后端 | optional extras + lazy import | `optional` 依赖 + feature 门控 |
| 装配缝 | `ports/factory.py` | `app` 组装根 `match` |
| 配置 | pydantic-settings + yaml | figment + toml |
| 日志 | logging + log_provenance | tracing + log_provenance |
| 提示词 | PackageLoader(运行时,随 wheel) | `include_str!`(编译期嵌入) |
| 门禁 | ruff+mypy+drift+pytest(beartype On) | fmt+clippy -D+doc+test+cargo-deny |
| SCA/合规 | Black Duck 等(外部) | `cargo-deny`(门内) |
| 分层上下文 | 根 CLAUDE.md + 就近契约 | 根 CLAUDE.md + **每 crate** CLAUDE.md |
