// ports:所有外部 AI 依赖的最小接口。核心与领域逻辑只依赖这些 interface,绝不依赖
// 具体 SDK。接口越窄能塞的实现越多,"换模型"从重构降级为加一个实现。
//
// 这里**零 SDK、零 UI 框架**(机械检查的不变量)。实现见 @__SCOPE__/adapters。

/** 文本生成。 */
export interface LLM {
  /**
   * 用给定 prompt 生成回答。
   *
   * @param prompt - 完整提示词。
   * @returns 生成的文本。
   * @throws {ProviderError} provider 调用失败时(由实现归一)。
   */
  complete(prompt: string): Promise<string>;
}

/** 文本向量化。 */
export interface Embedder {
  /**
   * 批量嵌入文本;返回与输入一一对应的向量。
   *
   * @param texts - 待嵌入文本数组。
   * @returns 每条文本对应的向量(数量与输入一致)。
   * @throws {ProviderError} provider 调用失败时(由实现归一)。
   */
  embed(texts: string[]): Promise<number[][]>;
}
