# Polyglot Core Standard(完整版)

面向 AI 主导开发的**多语言单核仓库**工程标准 —— 一个共享原生核心(通常是 Rust)被多门宿主语言(Swift / Kotlin / Python)通过**生成**(UniFFI/cbindgen/protobuf)或**手写**(PyO3/JNI)绑定消费。它与 rust / swift / python-project-standard 同一条脊:**信任放在可被机器检验的契约上,而非模型,也不是任何单一语言的检查器。**

> **定位**:本标准是**元标准(meta-standard)**。它只治理**语言之间的缝(seams)**,把每门语言**内部**的规则整层委托给姊妹标准:核心 →`rust-project-standard`,宿主 →`swift-project-standard` / `python-project-standard` 及其同族。本文在相关处指引"详见 …",**不重写**它们的内容,只组合它们、并补上它们各自看不见的跨语言层。

基线:一个 **Rust 权威核心**(`core/`,全量遵从 rust-project-standard);一个或多个**宿主 sub-tree**(各遵从自己的语言标准,spine-only);绑定经 **UniFFI**(生成)与/或 **PyO3 / JNI / cbindgen**(手写);**钉死的生成器版本**;一个顶层**复合门**(`make check`);一个**绑定新鲜度守卫**;以及根目录与每个 sub-tree 各一份 `CLAUDE.md`。

---

## §1 为什么需要一个元标准:单语言检查器看不见的缝

每门语言的标准都已锁死自己的 sub-tree——这是**必要但不充分**的。一个多语言仓库失败在**单语言检查器物理上看不见的缝**上:

- **核心与宿主漂移**:`cargo test` 全绿,因为它只测 Rust;`swift build` 全绿,因为它编译的是**昨天**的绑定。两边各自"绿",合起来是坏的。
- **手抄结构腐烂**:同一个 struct 被手工复制进 Swift、Kotlin、Python 三处,改核心时漏改其中两处——没有任何单语言检查器会报错,因为每一份本地都"自洽"。
- **panic 跨 FFI = UB**:一个 Rust `panic!` 沿栈展开越过 `extern "C"` 边界,是**未定义行为**或直接 abort。`cargo clippy` 不会拦——它认为 panic 是合法 Rust。
- **"绿"只代表一门语言**:"build is green" 默认指某一门语言的 build,而另一门的绑定可能已经 stale。

所以本标准的工作是:(a) 把共享真相收敛成**唯一权威核心**,每个绑定**派生**而非手抄;(b) 让 **FFI 边界本身**就是 typed、fallible、abort-safe 的;(c) 给每个生成物加**漂移守卫**;(d) 把各语言的门**复合成一个跨越每条缝的门**。

一句话原则贯穿全文:**仓库的正确性上限 = 它最弱的那条缝,而非它最强的 sub-tree。** 一个没被接进 `make check` 的宿主,就是一条不设防的缝。

---

## §2 NN1 —— 唯一权威核心拥有共享真相;宿主是薄壳

所有共享领域逻辑与**规范数据模型**只存在于一处实现——Rust 核心(遵从 rust-project-standard)。任何共享业务规则**绝不**在宿主语言里重实现。

**"该进核心"的气味**:你正要在 Swift **和** Python 里写同一段校验 / 加密 / 解析 / 状态机。那一刻就停手——它属于核心。宿主只持有宿主特有的关切:UI、平台集成、对绑定的符合语言习惯的人体工学包装。

**安全 / 不变量核心 = 边界(perimeter)**。当核心承载密钥、明文、鉴权这类不变量时,宿主拿到的是**不透明句柄(opaque handle)+ typed 结果**,**绝不**是违反不变量的原始手段。对照一个 `Vault.unlock`:

```rust
// 宿主拿到的是不透明的 SessionToken 句柄,而非主密钥、也非解密后的明文。
// 解锁、派生密钥、解密都发生在核心内部;明文从不越过 FFI 边界进入宿主地址空间。
#[uniffi::export]
pub fn unlock(vault: Arc<Vault>, password: String) -> Result<Arc<SessionToken>, CoreError> { … }
```

`SessionToken` 是 `#[derive(uniffi::Object)]`(不透明引用类型,宿主只能持有与传回,看不到字段);相对地,下文中心样例的 `TotpConfig` 是 `#[derive(uniffi::Record)]`(按值传递的纯数据)。规则:**句柄给能力,Record 给数据,密钥永不离核。** "把同一逻辑写进两门语言"的气味,和"把密钥递给宿主"的气味,是这条 NN 要消除的两件事。

---

## §3 NN2 —— 契约声明一次;绑定派生,绝不手抄

跨语言接口(宿主可调用的类型与函数)在核心里**恰好声明一处**:UniFFI 的 `#[uniffi::export]` / `.udl`,或 PyO3 的 `#[pymethods]` + 派生的 `.pyi`,或一份 `.proto`。**宿主永不手工复制一个 struct。** 绑定的产出是**构建步骤,不是手工移植**(`make gen-bindings`)。

这让模型级漂移**结构上不可能**:宿主无法引用核心没导出的字段——因为那个字段的绑定符号根本不存在。

> **一个真实的张力,要正面说清**:核心内部可以同时有一个**纯领域类型**(`__REPO__-core::otp::TotpConfig`,零 FFI 依赖)和一个**绑定投影**(`-ffi` 里的 `#[derive(uniffi::Record)]` 视图),两者用一个 `From` 连接。这**不**违反"声明一次"——因为这是**核心内部、同一门语言、编译器强校验**的投影:字段对不上 `From` 就编译不过。我们禁的是**跨语言、无人校验的手抄**。区别在于:within-core 的 typed 投影是 compiler-checked 的一门语言;cross-language 的 hand-mirror 是没有任何检查器的四门语言。前者合规,后者正是本标准存在的理由。

---

## §4 NN3 —— FFI 边界是 typed / fallible / parse-don't-validate 的缝;panic 绝不跨界

边界值是 "parse, don't validate" 的跨语言放大:核心的 `Result<T, E>` 浮现为宿主的惯用错误(Swift `throws`、Python `raise`、Kotlin checked exception),而宿主在**每个**裸绑定调用外包一层**薄的、手写的、受治理的** adapter,把结果**重新 typed 成宿主原生值**。

**Rust `panic!` 绝不允许沿栈展开越过 FFI 边界。** 这不是风格问题:

- 对 `extern "C"`(cbindgen / 手写 C-ABI)导出,panic 跨界是**未定义行为**——没有任何兜底。
- UniFFI 与 PyO3 各自在生成 / 包裹的 shim 里**装了 panic backstop**(UniFFI 转成生成的内部错误;PyO3 转成 Python `PanicException`),所以严格 UB 不发生——但那个兜底是**不透明、abort 邻近**的,**绝不能当作你的错误通道**。

纪律因此对两种姿态统一:**每个可恢复失败在跨界之前就被转成 typed 错误;`Result → host-error` 的映射显式且穷尽(total)。** 在能跨界到达的代码里出现 `unwrap`/`expect`/`try!`/裸索引,是缺陷,不是捷径——用 typed 错误传播替代,逃生须 `#[allow(clippy::unwrap_used)] // 理由`(详见 rust-project-standard §3)。

---

## §5 NN4 —— 两种绑定姿态,两套治理规则

这是元标准的核心分岔。绑定有且只有两种姿态,治理规则截然不同:

| | **生成姿态(generated)** | **手写姿态(handwritten)** |
|---|---|---|
| 例 | UniFFI / cbindgen / protobuf codegen | PyO3 / JNI / 手写 C-wrapper |
| 产出物 | 宿主语言源码(`apple/Generated/__REPO___core.swift`) | 核心语言内的绑定层(`core/crates/__REPO__-py`) |
| 治理归属 | **vendored artifact**:`linguist-generated`、**排除出宿主门**、**绝不手改**、由钉死的生成器重生成 | **受治理的核心代码**:全量遵从 rust-project-standard,**外加** NN3 的 FFI 规则 |
| 宿主逃生舱禁令 | **不适用于生成文件**(它的 `try!`/`as!` 是生成器输出);治理移到 NN3 的手写 wrapper | 适用(它本就是核心 Rust) |
| 被漂移守卫的"契约视图" | 生成的宿主源码本身 | 发布的**类型 stub / 头**(`.pyi`、生成的 `.h`) |

关键不对称:**生成姿态把治理从"被生成的文件"移走、转嫁到手写 wrapper;手写姿态把治理留在核心,但额外把"绝不 panic 跨界"压成硬纪律。** 两者都用 NN5 的新鲜度守卫盯住"契约视图"是否 stale。

下一节用**同一个 tiny 核心能力**把两种姿态各走一遍。

---

## §6 中心样例:同一能力的两种绑定

选定能力:`parse_otpauth(uri) -> Result<TotpConfig, CoreError>`——解析一条 `otpauth://` URI 成结构化 TOTP 配置。纯函数、有数据 Record、有 fielded 错误枚举,正好把 typed/fallible/parse-don't-validate 的全链路展示两遍。

唯一权威逻辑在纯核心 crate(零 FFI 依赖,`#![forbid(unsafe_code)]`):

```rust
// core/crates/__REPO__-core/src/otp.rs —— 规范类型 + 逻辑,声明一次,生成器无关
pub struct TotpConfig {
    pub issuer: String,
    pub account: String,
    pub algorithm: Algorithm,
    pub digits: u8,
    pub period: u16,
}

pub enum Algorithm { Sha1, Sha256, Sha512 }

#[derive(thiserror::Error, Debug)]
pub enum OtpError {
    #[error("malformed otpauth URI: {0}")]
    MalformedUri(String),
    #[error("unsupported algorithm: {0}")]
    UnsupportedAlgorithm(String),
    #[error("missing required secret")]
    MissingSecret,
}

pub fn parse_otpauth(uri: &str) -> Result<TotpConfig, OtpError> {
    // 纯 Rust:无 unwrap、无 panic;每个失败都是 OtpError 的一支。
    …
}
```

### §6.1 生成姿态:UniFFI 0.28 → Swift

**(1) 核心声明接口一次**(`-ffi` crate,UniFFI 受控出口)。UniFFI 的 Record / Enum / Error 视图在此声明,并用 `From` 从纯核心类型投影——投影由编译器校验:

```rust
// core/crates/__REPO__-ffi/src/lib.rs
uniffi::setup_scaffolding!();   // 0.28 library 模式:本 crate 一次

use std::sync::Arc;

#[derive(uniffi::Record)]
pub struct TotpConfig {
    pub issuer: String,
    pub account: String,
    pub algorithm: TotpAlgorithm,
    pub digits: u8,
    pub period: u16,
}

#[derive(uniffi::Enum)]
pub enum TotpAlgorithm { Sha1, Sha256, Sha512 }

#[derive(uniffi::Error, thiserror::Error, Debug)]
pub enum CoreError {
    #[error("malformed otpauth URI: {reason}")]
    MalformedUri { reason: String },
    #[error("unsupported algorithm: {name}")]
    UnsupportedAlgorithm { name: String },
    #[error("missing required secret")]
    MissingSecret,
}

// within-core 投影:字段对不上就编译不过——这是"声明一次"的合法形态。
impl From<__REPO___core::otp::OtpError> for CoreError {
    fn from(e: __REPO___core::otp::OtpError) -> Self {
        use __REPO___core::otp::OtpError as E;
        match e {
            E::MalformedUri(reason) => Self::MalformedUri { reason },
            E::UnsupportedAlgorithm(name) => Self::UnsupportedAlgorithm { name },
            E::MissingSecret => Self::MissingSecret,
        }
    }
}

/// 契约声明的唯一处。Result<T, CoreError> → 生成的 Swift `throws`。
#[uniffi::export]
pub fn parse_otpauth(uri: String) -> Result<TotpConfig, CoreError> {
    __REPO___core::otp::parse_otpauth(&uri)
        .map(Into::into)        // 纯类型 → Record 投影
        .map_err(Into::into)    // OtpError → CoreError;无 panic 可能跨界
}
```

`-ffi` crate 的 `Cargo.toml` 钉死 `uniffi = "0.28"`、`[lib] name = "__REPO___core"`、`crate-type = ["cdylib", "lib"]`,并附 `src/bin/uniffi-bindgen.rs`(`fn main() { uniffi::uniffi_bindgen_main() }`)供 `gen_bindings.sh` 调用。它也是 `#![forbid(unsafe_code)]` 的**唯一受控出口**(降到 `unsafe = "deny"` + 逐站点 `// SAFETY:`,详见 rust-project-standard §2)。

**(2) 生成的 Swift 是 vendored artifact**。`make gen-bindings` 跑出 `apple/Generated/__REPO___core.swift`,内含 `public func parseOtpauth(uri: String) throws -> TotpConfig`、`public struct TotpConfig`、`public enum CoreError: Swift.Error`(UniFFI 把函数名与枚举 case 转成 lowerCamelCase)。它**从门里被排除、从不手改**:

```gitattributes
# .gitattributes —— NN4 的一半
apple/Generated/**            linguist-generated=true
```
```yaml
# apple/.swiftlint.yml —— 另一半:逃生舱禁令不适用于生成文件
excluded:
  - Generated
```
生成目录置于 `apple/Sources/` **之外**,故 `swift format lint --strict --recursive Sources Tests` 天然不碰它(这是首选机制);若构建要求它落在 Sources 内,则由 gen 步在文件首注入 swift-format 的 `// swift-format-ignore-file` 指令。无论哪种,**它的 `try!`/`as!` 是生成器输出,不归宿主门管**。

**(3) 手写 wrapper 是受治理的 FFI 缝**。所有核心调用都过它;它把生成的 `throws` 重新 typed 成宿主 newtype + 一个 Swift `enum` 错误。`Result<T, CoreError> → throws` 的映射在此**显式且穷尽**:

```swift
// apple/Sources/__REPO__/CoreClient.swift —— 受治理的 FFI 缝(逃生舱禁令、严格并发、newtype 规则在此生效)
// 注:生成的 parseOtpauth / TotpConfig / CoreError 与本文件编译进同一宿主 module,无需 import。
import Foundation

/// 宿主原生错误:wrapper 把生成的 CoreError 重新 typed 成 Swift enum。
public enum VaultError: Error, Sendable, Equatable {
    case malformedURI(reason: String)
    case unsupportedAlgorithm(name: String)
    case missingSecret
}

/// 宿主 newtype:绝不让生成类型渗进宿主逻辑。
public struct TOTP: Sendable, Equatable {
    public enum Algorithm: Sendable { case sha1, sha256, sha512 }
    public let issuer: String
    public let account: String
    public let algorithm: Algorithm
    public let digits: Int
    public let period: Int
}

public struct CoreClient: Sendable {
    public init() {}

    public func parseOTPAuth(_ uri: String) throws -> TOTP {
        do {
            let record = try parseOtpauth(uri: uri)        // 生成的 throws 函数
            return TOTP(
                issuer: record.issuer,
                account: record.account,
                algorithm: Self.map(record.algorithm),
                digits: Int(record.digits),
                period: Int(record.period)
            )
        } catch let error as CoreError {
            throw Self.map(error)                          // 每个 case 都映射
        }
    }

    // 穷尽 switch:无 default。核心新增一支 CoreError,这里就编译失败——
    // 漂移在编译期被钉在缝上,而非运行期静默丢错。
    private static func map(_ error: CoreError) -> VaultError {
        switch error {
        case let .malformedUri(reason):        .malformedURI(reason: reason)
        case let .unsupportedAlgorithm(name):  .unsupportedAlgorithm(name: name)
        case .missingSecret:                   .missingSecret
        }
    }

    private static func map(_ algorithm: TotpAlgorithm) -> TOTP.Algorithm {
        switch algorithm {
        case .sha1:   .sha1
        case .sha256: .sha256
        case .sha512: .sha512
        }
    }
}
```

宿主只 `import` 这个 `CoreClient`,从不直接碰生成符号。Swift 内部规则(typed throws、`Sendable`、newtype)由 swift-project-standard 治理这个 wrapper;**不**治理生成文件。

### §6.2 手写姿态:PyO3 0.23 → Python

**(1) 同一能力经 `#[pyfunction]` / `#[pyclass]` 暴露**(`-py` crate)。这个 crate 是**受治理的 Rust**(遵从 rust-project-standard),同时是受控出口;它把核心错误转成一棵 Python 异常层级:

```rust
// core/crates/__REPO__-py/src/lib.rs
use pyo3::create_exception;
use pyo3::prelude::*;

create_exception!(_native, CoreError, pyo3::exceptions::PyException);
create_exception!(_native, MalformedUriError, CoreError);
create_exception!(_native, UnsupportedAlgorithmError, CoreError);
create_exception!(_native, MissingSecretError, CoreError);
create_exception!(_native, InternalError, CoreError);

#[pyclass(frozen, get_all)]
#[derive(Clone)]
pub struct TotpConfig {
    pub issuer: String,
    pub account: String,
    pub algorithm: String,   // "SHA1" | "SHA256" | "SHA512"
    pub digits: u8,
    pub period: u16,
}

// 把核心 typed 错误转成 PyErr —— 绝不让 panic 当错误通道。
fn to_pyerr(e: __REPO___core::otp::OtpError) -> PyErr {
    use __REPO___core::otp::OtpError as E;
    match e {
        E::MalformedUri(reason) => MalformedUriError::new_err(reason),
        E::UnsupportedAlgorithm(name) => UnsupportedAlgorithmError::new_err(name),
        E::MissingSecret => MissingSecretError::new_err("missing required secret"),
    }
}

#[pyfunction]
fn parse_otpauth(uri: &str) -> PyResult<TotpConfig> {
    // panic→PyErr 纪律:PyO3 会把 #[pyfunction] 体内展开的 panic 转成 Python
    // PanicException(而非 UB)——但那是不透明、abort 邻近的兜底,绝不依赖它。
    // 这里把"预期失败"显式转成 typed PyErr,并把"意外 panic"防御性地 catch 成
    // 一个 typed InternalError,使边界永远只看到 PyErr。
    std::panic::catch_unwind(|| __REPO___core::otp::parse_otpauth(uri))
        .map_err(|_| InternalError::new_err("core panicked while parsing otpauth URI"))?
        .map(|cfg| TotpConfig {
            issuer: cfg.issuer,
            account: cfg.account,
            algorithm: cfg.algorithm.name().to_owned(),
            digits: cfg.digits,
            period: cfg.period,
        })
        .map_err(to_pyerr)
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<TotpConfig>()?;
    m.add_function(wrap_pyfunction!(parse_otpauth, m)?)?;
    m.add("CoreError", m.py().get_type::<CoreError>())?;
    m.add("MalformedUriError", m.py().get_type::<MalformedUriError>())?;
    m.add("UnsupportedAlgorithmError", m.py().get_type::<UnsupportedAlgorithmError>())?;
    m.add("MissingSecretError", m.py().get_type::<MissingSecretError>())?;
    Ok(())
}
```

对照 §6.1 的生成姿态:那里 panic backstop 由 UniFFI 生成的 shim 承担、对核心作者不可见;这里 backstop 由 PyO3 承担,但因为这层是**手写的核心 Rust**,纪律落在作者手上——`catch_unwind` + typed 转换是显式的。两种姿态、同一条铁律:**panic 永不是你的错误通道**(详见 pyo3-best-practices)。

**(2) 发布的 `_native.pyi` stub 是被漂移守卫的契约**。它是宿主 mypy 眼里的核心视图,由 `make gen-bindings` 从编译模块**派生**(`python -m __REPO__._stubgen`),`linguist-generated`,绝不手改:

```python
# python/src/__REPO__/_native.pyi —— 派生 + 新鲜度守卫的契约 stub
from typing import final

@final
class TotpConfig:
    @property
    def issuer(self) -> str: ...
    @property
    def account(self) -> str: ...
    @property
    def algorithm(self) -> str: ...
    @property
    def digits(self) -> int: ...
    @property
    def period(self) -> int: ...

class CoreError(Exception): ...
class MalformedUriError(CoreError): ...
class UnsupportedAlgorithmError(CoreError): ...
class MissingSecretError(CoreError): ...

def parse_otpauth(uri: str) -> TotpConfig: ...
```

`python/pyproject.toml` 的 ruff `extend-exclude = ["src/__REPO__/_native.pyi"]` 把它排除出宿主门(NN4)。

**(3) 宿主 wrapper module 把 native 返回重新 typed 成 pydantic 模型**(parse, don't validate)。这是 §6.1 Swift wrapper 的 Python 对应:

```python
# python/src/__REPO__/otp.py —— 受治理的 Python 缝
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from __REPO__ import _native


class Algorithm(str, Enum):
    SHA1 = "SHA1"
    SHA256 = "SHA256"
    SHA512 = "SHA512"


class Totp(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    issuer: str
    account: str
    algorithm: Algorithm
    digits: int = Field(ge=6, le=8)
    period: int = Field(gt=0)


class OtpError(Exception): ...
class MalformedURI(OtpError): ...
class UnsupportedAlgorithm(OtpError): ...
class MissingSecret(OtpError): ...


def parse_otpauth(uri: str) -> Totp:
    """把 native 返回重新 typed 成已校验的宿主模型;把 native 错误重新 typed 成宿主异常。"""
    try:
        native = _native.parse_otpauth(uri)
    except _native.MalformedUriError as exc:
        raise MalformedURI(str(exc)) from exc
    except _native.UnsupportedAlgorithmError as exc:
        raise UnsupportedAlgorithm(str(exc)) from exc
    except _native.MissingSecretError as exc:
        raise MissingSecret(str(exc)) from exc
    return Totp(                                  # 跨界即进 pydantic:parse, don't validate
        issuer=native.issuer,
        account=native.account,
        algorithm=Algorithm(native.algorithm),
        digits=native.digits,
        period=native.period,
    )
```

宿主逻辑只看见 `otp.parse_otpauth -> Totp` 与 `OtpError` 子类,永不直接碰 `_native`。Python 内部规则(mypy --strict、beartype、ruff)治理这个 wrapper(详见 python-project-standard);**不**治理 `_native.pyi`。

---

## §7 Result → host-error 映射表

核心的 `Result<T, CoreError>` 在每条缝上必须有**显式且穷尽**的落点。下表是中心样例的全映射;`default`/裸 `except Exception`/`catch { }` 吞错都是缺陷:

| 核心 `Result<T, CoreError>` | Rust(`OtpError`) | Swift `throws`(`VaultError`) | Python `raise`(子类) | Kotlin checked exception |
|---|---|---|---|---|
| `Ok(TotpConfig)` | `Ok(_)` | 返回 `TOTP` | 返回 `Totp` | 返回 `Totp` |
| `MalformedUri { reason }` | `MalformedUri(String)` | `throw .malformedURI(reason:)` | `raise MalformedURI` | `throw MalformedUriException` |
| `UnsupportedAlgorithm { name }` | `UnsupportedAlgorithm(String)` | `throw .unsupportedAlgorithm(name:)` | `raise UnsupportedAlgorithm` | `throw UnsupportedAlgorithmException` |
| `MissingSecret` | `MissingSecret` | `throw .missingSecret` | `raise MissingSecret` | `throw MissingSecretException` |
| —(一个 `panic!`) | bug:照常上抛,**绝不跨界** | 跨界**前**已转成 typed 错误 | 跨界**前**已转成 `PyErr`(`catch_unwind`) | 跨界**前**已转成 `JThrowable` |

**通用规则**:panic **永不跨界**——它在 boundary 之前就被转换;生成姿态由生成 shim 兜底、手写姿态由 `catch_unwind` 兜底,但兜底**不是错误通道**。映射的穷尽性由宿主侧的穷尽 `switch`/穷尽 `except` 保证:核心新增一支错误而某宿主没接,应当在该宿主的门里**编译失败或类型失败**,而非运行期才暴露。

---

## §8 复合门 + 绑定新鲜度守卫

### §8.1 NN6 —— 一个跨越每条缝的复合门(仓库唯一的正确性判据)

顶层一条命令判全仓。`Makefile`(`set -euo pipefail` via `SHELL`)按 核心 → 各宿主 → 新鲜度 串起每条缝:

```makefile
check: check-core check-hosts check-bindings ## 唯一判据:核心 + 宿主 + 绑定新鲜度
	@echo "✓ composed gate green"

check-core:                ## Rust 核心自有零警告门(rust-project-standard)
	cd core && ./ci.sh
check-hosts: check-apple check-python
check-apple:               ## Swift 宿主门(swift-project-standard, spine-only)
	cd apple && ./ci.sh
check-python:              ## Python 宿主门(python-project-standard, spine-only)
	cd python && ./ci.sh
check-bindings:            ## 漂移守卫:重生成的绑定必须等于已提交的(NN5)
	bash scripts/check_bindings.sh
```

要点:

- **完成 = 复合门绿**,永远不是某一门语言"看着没问题"。每个 `cd <sub-tree> && ./ci.sh` 调用的是该 sub-tree **自己的**门——本标准**不重定义**它,只**组合**它。
- **CI 镜像它,pre-push hook 钉死它**。`ci.sh`(根)是 `make check` 的薄包装,CI 调同一条。
- **没被接进 `check-hosts` 的宿主 = 不设防的缝**。新增第三个宿主(如 `android/`)时,必须同时加 `check-android` 并挂进 `check-hosts`——否则它的门永远不跑,而上限是最弱的缝。

### §8.2 NN5 —— 绑定新鲜度守卫(关掉"忘了重生成"这个洞)

生成能保证"从核心派生的绑定是对的",但关不掉一个洞:**改了核心却忘了跑 `gen-bindings`**。守卫把它补上——从**当前**核心重生成所有绑定 + stub,再 `git diff --exit-code`:

```bash
# scripts/check_bindings.sh
set -euo pipefail
cd "$(dirname "$0")/.."
echo "→ regenerating all bindings from the core (single source of truth)…"
bash scripts/gen_bindings.sh
echo "→ verifying committed bindings match the regenerated output…"
DERIVED=(apple/Generated python/src/*/_native.pyi)   # 镜像 versions.toml [bindings]
if ! git diff --exit-code -- "${DERIVED[@]}" 2>/dev/null; then
  echo "✗ STALE BINDINGS — 核心变了,但已提交的绑定没跟着重生成。" >&2
  echo "  Fix: 跑 'make gen-bindings',并把结果与核心接口改动放进同一个 commit。" >&2
  exit 1
fi
echo "✓ bindings are fresh"
```

这是各语言内部漂移检查(rust-project-standard / python-project-standard 的 `check_drift`)的**跨语言对应**。它强制了一条工作流铁律:**一次契约改动是一个跨 sub-tree 的连贯 commit**——核心改动 + 重生成的绑定 + 每个宿主 wrapper 的适配,**绝不**拆进"某些绑定 stale 也算绿"的中间态。`gen_bindings.sh` 是绑定代码产出的**唯一**途径(生成姿态吐宿主源码;手写姿态只重生成 `.pyi` stub——绑定层本身是手写核心 Rust,不被覆盖)。

---

## §9 NN7 —— `versions.toml`:工具链 + 生成器矩阵的唯一声明

每门语言钉死工具链,**且生成器版本钉死**。根目录 `versions.toml` 是复合门与 CI 都读的单一矩阵:

```toml
[toolchains]
rust   = "1.85.0"   # mirror core/rust-toolchain.toml
swift  = "6.0"      # mirror apple/.swift-version
python = "3.13"     # mirror python/.python-version
kotlin = "2.1.0"

[generators]
uniffi = "0.28"     # 生成姿态(Swift / Kotlin / Python)
pyo3   = "0.23"     # 手写姿态(Python native extension)

[bindings]
apple  = "generated"     # uniffi → apple/Generated/__REPO___core.swift
python = "handwritten"   # pyo3 module in core + python/src/__REPO__/_native.pyi stub
```

**为什么钉死生成器版本是最微妙的反漂移**:`uniffi 0.27` 与 `0.28` 对**同一个 `#[uniffi::export]`** 可以吐出**不同的 Swift 代码**(改了 lowering、改了 case 命名、改了 callback 协议)。这意味着——**核心接口一个字没改,宿主却悄悄与核心 desync 了**,只因为某台机器装的生成器版本不同。这种漂移没有任何接口 diff 可循,新鲜度守卫也只在生成器版本一致时才可信。所以:**显式钉死,在 `versions.toml` 声明、在 `core/Cargo.toml` 钉死、在每个 sub-tree 镜像对应值**(`rust-toolchain.toml`、`.swift-version`、`.python-version`)。矩阵是 record;sub-tree 里的钉死是执行点。

---

## §10 多语言仓库里的 AI 缝

模型无关的 provider 缝(`domain` trait/Protocol + 默认 `MockProvider`,详见各语言标准 §9)在多语言仓库里**只定位一次:在真正调用模型的那个 sub-tree**,绝不跨语言复制。

- **若核心调模型**:缝在核心的 `domain` crate(rust-project-standard),宿主**跨 FFI 边界消费 typed 结果**,spine-only。
- **若一个独立服务调模型**(worker、后端):那个服务拥有缝,核心与宿主保持 model-free。

多语言铁律:**找到模型被调用的那一处,把缝放那儿,让其余每个 sub-tree 跨缝接收 typed 值。** 在一个只渲染核心算出的结果的宿主上硬塞 `MockProvider`,是 cargo-culting,不是合规——**绝不**为每个宿主复制一份 `MockProvider`。约束下沉的纪律(constrain-don't-ask、收窄发射面、护栏确定性独立)继承自姊妹标准,只在调模型的那个 sub-tree 生效;跨界时**传 typed 值,绝不在对岸重新发射模型文本**。

---

## §11 一个完整的多语言仓库树

```
repo/
├── Makefile                       # 复合门(NN6)
├── versions.toml                  # 工具链 + 生成器矩阵(NN7)
├── .gitattributes                 # 生成物 linguist-generated(NN4)
├── ci.sh                          # = make check 的薄包装,CI 调用
├── CLAUDE.md                      # 根路由表(硬约束 + 去哪找)
├── docs/adr/                      # 决策记录(任何契约改动前先写一条)
├── scripts/
│   ├── gen_bindings.sh            # 从核心派生所有绑定 + stub(NN2;绑定产出唯一途径)
│   └── check_bindings.sh          # 新鲜度守卫(NN5)
├── core/                          # Rust 工作区 = 唯一权威核心(rust-project-standard 全量)
│   ├── Cargo.toml                 #   [workspace];钉死 uniffi=0.28 / pyo3=0.23
│   ├── rust-toolchain.toml        #   镜像 versions.toml rust
│   ├── ci.sh  CLAUDE.md
│   └── crates/
│       ├── __REPO__-core/         #   纯领域逻辑 + 规范类型,零 FFI(#![forbid(unsafe_code)])
│       │   └── src/otp.rs         #     parse_otpauth(&str) -> Result<TotpConfig, OtpError>
│       ├── __REPO__-ffi/          #   UniFFI 受控出口:setup_scaffolding! + #[uniffi::export]
│       │   ├── src/lib.rs         #     契约在此声明一次(生成姿态)
│       │   └── src/bin/uniffi-bindgen.rs
│       └── __REPO__-py/           #   PyO3 受控出口:#[pymodule] _native + #[pyfunction]
│           └── src/lib.rs         #     手写姿态;panic→PyErr 纪律
├── apple/                         # Swift 宿主(swift-project-standard, spine-only)
│   ├── .swift-version  .swiftlint.yml  ci.sh  CLAUDE.md
│   ├── Generated/
│   │   └── __REPO___core.swift    # ★ vendored UniFFI artifact:门外、never edited
│   └── Sources/__REPO__/
│       └── CoreClient.swift       # ★ 手写治理 wrapper:Result→throws 全映射
├── python/                        # Python 宿主(python-project-standard, spine-only)
│   ├── .python-version  pyproject.toml  ci.sh  CLAUDE.md
│   └── src/__REPO__/
│       ├── _native.pyi            # ★ 派生 + 新鲜度守卫的契约 stub
│       └── otp.py                 # ★ 手写治理 wrapper:native→pydantic
└── (android/ …第三个宿主按需,记得挂进 Makefile check-hosts)
```

每个 sub-tree 与根各一份 `CLAUDE.md`:根是**路由表**(硬约束 + 去哪找),sub-tree 各写本地缝契约(`core/CLAUDE.md`:契约在此声明、不许 panic 跨界、受控出口 crate;`apple/CLAUDE.md`:`Generated/` 是 vendored、所有核心调用过 wrapper;`python/CLAUDE.md`:手写姿态、`.pyi` 派生且守卫、跨界进 pydantic)。

### §11.1 真实落地:Claustra(本标准 retro-fit 的现有仓库)

Claustra 是一个本地优先密码管理器,其实际形态正是本标准要 retro-fit 的样子:

- **一个 Rust `claustra-core` crate,经 UniFFI 导出到 Swift app(`ClaustraApp/`)**。生成的 `ClaustraApp/Sources/Claustra/RustLib/claustra_core.swift` **恰恰**是本标准规定要排除出 Swift 门的那个 vendored artifact——它已经是生成物,只是 retro-fit 之前没被正式标成 `linguist-generated`、没被显式从 SwiftLint/swift-format 排除、也没有新鲜度守卫盯着它。`build-rust.sh` 是 `gen_bindings.sh` 的现成对应。
- **两种姿态它都真有**:Swift 是生成姿态(UniFFI);`crates/claustra-python`(PyO3)是手写姿态——正是 §6.2 的实例。
- **宿主是 spine-only,因为 LLM 不在 Swift 里**:AI 解析跑在独立的 Cloudflare Worker(`claustra-worker/`)。按 §10,AI 缝在 worker,核心与 Swift/CLI 保持 model-free、跨界只接收 typed 值——所以**不**该在 Swift 侧硬塞 `MockProvider`。

retro-fit 的增量因此很具体:补一份 `versions.toml` 钉死 `uniffi` 版本;把 `RustLib/claustra_core.swift` 正式标成 vendored 并排除出 Swift 门;加一个 `check_bindings.sh` 让 `build-rust.sh` 的输出受新鲜度守卫;把 `cargo test` + `xcodebuild` + PyO3 的 stub-diff 复合进一条 `make check`。现有仓库本就跑对了大半;本标准把那些**隐性正确**变成**会失败的工件**。

---

## §12 规模与委托

**本标准只治理缝。** 每门语言的内部——核心的 workspace/clippy/`forbid unsafe`、Swift 的严格并发/逃生舱、Python 的 mypy/beartype/pydantic——整层委托:

- 核心 → **rust-project-standard**(`#![forbid(unsafe_code)]`、零警告门、`Result`/`thiserror`、serde+newtype、crate-per-domain、`domain` 零 SDK)。
- Swift 宿主 → **swift-project-standard**(Swift 6 严格并发、`throws`/typed throws、`Codable`+newtype、双门)。
- Python 宿主 → **python-project-standard**(mypy --strict、ruff、beartype、pydantic 边界)。
- PyO3 绑定层的写法细节 → **pyo3-best-practices**;Rust unsafe 出口的细节 → rust-project-standard §2。

按**两个轴**伸缩:宿主数量 × 是否有 sub-tree 调模型。

- **一核 + 一宿主、同一工作流构建**:一条 5 行 `make check` 串两个门 + 一个 regen-diff 就是全部标准;别为单宿主套 `bindings/<lang>/` 分类法。
- **第二个宿主出现的那一刻**:契约必须收敛成单一声明源,新鲜度守卫必须进门——这正是手抄开始静默腐烂的临界点。
- **核心开始调模型的那一刻**:只在核心打开 AI 触发层。

把全套装置硬套到单宿主核心上是 cargo-culting;从多宿主核心里省掉新鲜度守卫,正是本标准存在要防的失败。
