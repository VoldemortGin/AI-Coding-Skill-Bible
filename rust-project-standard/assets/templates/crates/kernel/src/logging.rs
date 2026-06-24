//! 日志/追踪初始化与 AI 产物血缘。
//!
//! 纪律:库 crate 只用 `tracing` 宏发事件,**绝不**在别处装 subscriber;
//! [`init`] 由 app 入口调用一次。trace 只记码值/计数/耗时,绝不落答案/原文/向量。
use tracing_subscriber::EnvFilter;

/// 初始化全局 tracing subscriber(读 `RUST_LOG`,缺省 `info`)。入口调用一次。
pub fn init() {
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));
    tracing_subscriber::fmt().with_env_filter(filter).init();
}

/// 记录 AI 产物的来源元数据(来源/实现/版本/计数),绝不记录载荷本身。
pub fn log_provenance(source: &str, implementation: &str, version: &str, count: Option<usize>) {
    tracing::info!(source, implementation, version, ?count, "provenance");
}
