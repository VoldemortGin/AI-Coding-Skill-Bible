//! 边界错误(port 契约的一部分)。
//!
//! 厂商/网络/超时/API 错在 adapter 边界归一到 [`ProviderError`];
//! 程序 bug 走 panic(`unsafe` 已 forbid,clippy 限制 `unwrap`/`expect`),不静默吞错。
use thiserror::Error;

/// 外部 provider(LLM / embedding / 向量库等)调用失败。
#[derive(Debug, Error)]
pub enum ProviderError {
    /// 调用过程出错(网络/超时/API 等);`String` 为归一后的原因。
    #[error("provider 调用失败: {0}")]
    Call(String),
}
