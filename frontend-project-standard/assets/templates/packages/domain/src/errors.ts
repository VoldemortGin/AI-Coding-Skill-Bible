// 边界错误。具体 class extends Error。纪律:厂商 SDK 的各色错误在 adapter 内归一到
// ``ProviderError``;领域校验错误用 ``DomainError``。程序 bug(不变量被破坏)照常
// `throw new Error(...)`,不混进这里。

/** provider(LLM / Embedder / 真实 SDK)调用边界的归一化错误。 */
export class ProviderError extends Error {
  constructor(
    message: string,
    /** 可选底层原因(原始 SDK 错误)。 */
    override readonly cause?: unknown,
  ) {
    super(message);
    this.name = "ProviderError";
  }
}

/** 领域校验错误:外部输入违反领域约束时抛出。 */
export class DomainError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DomainError";
  }
}
