//! 示例真实 adapter(feature `openai` 门控)。SDK 只在此引入(本骨架为占位)。
//!
//! 接真实 SDK:在 Cargo.toml 把 `openai = []` 改为 `openai = ["dep:async-openai"]`,
//! 在下方 lazy 构造 client、调用 API,并把 SDK 错误 `map_err` 成 `ProviderError::Call`。
use domain::errors::ProviderError;
use domain::ports::Llm;

/// OpenAI LLM adapter(占位)。
#[derive(Debug, Default)]
pub struct OpenAiLlm;

impl OpenAiLlm {
    /// 构造 adapter。
    ///
    /// # Errors
    /// 初始化失败(缺 key 等)时返回 [`ProviderError`]。
    pub fn new() -> Result<Self, ProviderError> {
        Ok(Self)
    }
}

impl Llm for OpenAiLlm {
    fn complete(&self, _prompt: &str) -> Result<String, ProviderError> {
        // TODO: 用 async-openai 构造 client 调用;SDK 错误 map_err 成 ProviderError::Call
        Err(ProviderError::Call("openai adapter 未实现(骨架占位)".to_owned()))
    }
}
