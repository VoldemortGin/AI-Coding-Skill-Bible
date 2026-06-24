// domain 公共 API:ports(interface)+ models(Zod schema)+ errors。零 SDK、零 UI 框架。

export type { Embedder, LLM } from "./ports.js";
export { Document, TopK } from "./models.js";
export { DomainError, ProviderError } from "./errors.js";
