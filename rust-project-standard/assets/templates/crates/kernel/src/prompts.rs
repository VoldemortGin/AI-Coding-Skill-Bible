//! 提示词:`include_str!` 编译期嵌入(随二进制出厂,无运行时路径问题),
//! minijinja 严格渲染(缺变量直接报错,而非静默空串)。
use minijinja::{Environment, UndefinedBehavior};

/// RAG 回答提示词(编译期嵌入)。
pub const ANSWER: &str = include_str!("prompts/rag/answer.md");

/// 构造严格渲染环境:缺变量报错。调用方 `add_template` + `render`,用 `?` 传播错误。
#[must_use]
pub fn strict_env() -> Environment<'static> {
    let mut env = Environment::new();
    env.set_undefined_behavior(UndefinedBehavior::Strict);
    env
}
