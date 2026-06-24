//! domain:领域类型(models)、ports(traits)与边界错误。
//!
//! **零厂商 SDK 依赖**:只定义抽象与数据,具体实现在 `adapters`。
pub mod errors;
pub mod models;
pub mod ports;

pub use errors::ProviderError;
