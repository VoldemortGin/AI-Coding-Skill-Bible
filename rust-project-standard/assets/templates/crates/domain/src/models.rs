//! 领域数据模型。用强类型 / newtype 让非法状态尽量不可表示。
use serde::{Deserialize, Serialize};

/// 检索到的文档片段。
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    /// 文档来源标识。
    pub id: String,
    /// 文本内容。
    pub text: String,
}
