// adapters 公共 API:MockProvider(默认实现)+ factory(装配缝)。唯一可碰 SDK 的包。

export { MockEmbedder, MockLLM } from "./mock.js";
export { makeEmbedder, makeLLM } from "./factory.js";
