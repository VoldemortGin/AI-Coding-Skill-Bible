//! adapters:ports(traits)的具体实现。唯一允许依赖厂商 SDK 的 crate(feature 门控)。
pub mod mock;

#[cfg(feature = "openai")]
pub mod openai;
