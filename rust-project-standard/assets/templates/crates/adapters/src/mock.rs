//! 确定性离线默认实现(default,不是测试桩):不连网、无需 key 也能跑通并通过测试;
//! 同输入同输出,不被随机性污染。
use domain::errors::ProviderError;
use domain::models::Document;
use domain::ports::{Embedder, Llm, Reranker};

/// 确定性 mock LLM。
#[derive(Debug, Default)]
pub struct MockLlm;

impl Llm for MockLlm {
    fn complete(&self, prompt: &str) -> Result<String, ProviderError> {
        let head: String = prompt.chars().take(40).collect();
        Ok(format!("[mock] {head}"))
    }
}

/// 确定性 mock embedder(同输入同输出)。
#[derive(Debug, Default)]
pub struct MockEmbedder;

impl Embedder for MockEmbedder {
    fn embed(&self, texts: &[String]) -> Result<Vec<Vec<f32>>, ProviderError> {
        Ok(texts
            .iter()
            .map(|t| {
                let sum: u32 = t.bytes().map(u32::from).sum();
                vec![(sum % 1000) as f32 / 1000.0]
            })
            .collect())
    }
}

/// 确定性 mock reranker(保持原序)。
#[derive(Debug, Default)]
pub struct MockReranker;

impl Reranker for MockReranker {
    fn rerank(&self, _query: &str, docs: &[Document]) -> Result<Vec<usize>, ProviderError> {
        Ok((0..docs.len()).collect())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embed_is_deterministic() {
        let e = MockEmbedder;
        let texts = vec!["hello".to_owned(), "world".to_owned()];
        assert_eq!(e.embed(&texts).unwrap(), e.embed(&texts).unwrap());
    }

    #[test]
    fn embed_preserves_count() {
        let e = MockEmbedder;
        let texts = vec!["a".to_owned(), "b".to_owned(), "c".to_owned()];
        assert_eq!(e.embed(&texts).unwrap().len(), 3);
    }
}
