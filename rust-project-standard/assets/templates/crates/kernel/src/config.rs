//! 全局配置的唯一来源:默认 < `configs/settings.toml` < 环境变量(`APP_` 前缀)。
//! 经 serde 反序列化为强类型,非法配置在启动即报错(parse, don't validate)。
use figment::{
    Figment,
    providers::{Env, Format, Toml},
};
use serde::Deserialize;

/// 检索相关配置。
#[derive(Debug, Deserialize)]
pub struct RetrieverConfig {
    /// 召回条数。
    pub top_k: usize,
    /// 重排模型标识。
    pub rerank_model: String,
}

/// 应用全局配置。
#[derive(Debug, Deserialize)]
pub struct Settings {
    /// LLM provider(装配缝按此选实现);默认 `mock`,离线可跑。
    #[serde(default = "default_provider")]
    pub llm_provider: String,
    /// 检索配置。
    pub retriever: RetrieverConfig,
}

fn default_provider() -> String {
    "mock".to_owned()
}

impl Settings {
    /// 加载配置。优先级:默认 < TOML 文件 < 环境变量(`APP_` 前缀,`__` 分隔嵌套)。
    ///
    /// # Errors
    /// 反序列化失败(缺字段、类型不匹配等)时返回 [`figment::Error`]。
    pub fn load() -> Result<Self, figment::Error> {
        Figment::new()
            .merge(Toml::file("configs/settings.toml"))
            .merge(Env::prefixed("APP_").split("__"))
            .extract()
    }
}
