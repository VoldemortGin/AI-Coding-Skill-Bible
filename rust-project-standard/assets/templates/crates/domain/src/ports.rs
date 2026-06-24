//! ports:所有外部 AI 依赖的最小 trait 接口。
//!
//! 核心与领域逻辑只依赖这些 trait,绝不依赖具体 SDK。接口越窄能塞的实现越多,
//! "换模型"从重构降级为加一个实现。
use crate::errors::ProviderError;
use crate::models::Document;

/// 文本生成。
pub trait Llm {
    /// 用给定 prompt 生成回答。
    ///
    /// # Errors
    /// provider 调用失败时返回 [`ProviderError`]。
    fn complete(&self, prompt: &str) -> Result<String, ProviderError>;
}

/// 文本向量化。
pub trait Embedder {
    /// 批量嵌入文本。
    ///
    /// # Errors
    /// provider 调用失败时返回 [`ProviderError`]。
    fn embed(&self, texts: &[String]) -> Result<Vec<Vec<f32>>, ProviderError>;
}

/// 文档重排。
pub trait Reranker {
    /// 按与 query 的相关性返回 `docs` 的重排下标。
    ///
    /// # Errors
    /// provider 调用失败时返回 [`ProviderError`]。
    fn rerank(&self, query: &str, docs: &[Document]) -> Result<Vec<usize>, ProviderError>;
}
