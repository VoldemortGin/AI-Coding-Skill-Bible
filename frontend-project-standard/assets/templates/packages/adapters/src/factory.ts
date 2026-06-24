// 装配缝:按 config 选实现。默认 mock(离线、零 SDK)。未知 provider 显式报错,
// 绝不沉默回退。adapters 是唯一可碰 SDK 的包;真实后端用 optionalDependencies +
// 动态 `await import()` 懒加载,默认模板不内置真实 SDK。

import type { AppConfig } from "@__SCOPE__/kernel";
import type { Embedder, LLM } from "@__SCOPE__/domain";
import { ProviderError } from "@__SCOPE__/domain";

import { MockEmbedder, MockLLM } from "./mock.js";

/**
 * 按 config 选 LLM 实现。默认 mock;未知 provider 显式抛错(返回 rejected promise)。
 *
 * 返回 `Promise<LLM>` 而非同步值:真实后端要用动态 `await import()` 懒加载 SDK
 * (见下方 `makeOpenAILLM` 注释示例),保持调用方一律 `await makeLLM(config)`。
 *
 * @param config - 已加载的应用配置。
 * @returns 选定的 LLM 实现。
 * @throws {ProviderError} provider 未知,或真实后端缺凭据 / 缺依赖时。
 */
export function makeLLM(config: AppConfig): Promise<LLM> {
  const provider = config.server.LLM_PROVIDER;
  switch (provider) {
    case "mock":
      return Promise.resolve(new MockLLM());
    // case "openai":
    //   return makeOpenAILLM();
    default:
      return Promise.reject(new ProviderError(`unknown LLM_PROVIDER: ${provider}`));
  }
}

// —— 真实后端示例(默认不启用)。启用步骤:——
//   1) package.json 加 optionalDependencies: { "openai": "^4.x" }(+ env 放 OPENAI_API_KEY)。
//   2) 在上面的 switch 解开 `case "openai": return makeOpenAILLM();`,并解开下面函数。
//   3) SDK 只在此动态 import,默认 bundle / test 不拉它;厂商各色错误归一到 ProviderError。
// async function makeOpenAILLM(): Promise<LLM> {
//   const apiKey = process.env["OPENAI_API_KEY"];
//   if (apiKey === undefined || apiKey === "") {
//     throw new ProviderError("missing OPENAI_API_KEY");
//   }
//   try {
//     const { OpenAI } = await import("openai");
//     const client = new OpenAI({ apiKey });
//     return {
//       async complete(prompt: string): Promise<string> {
//         const res = await client.responses.create({ model: "gpt-4o-mini", input: prompt });
//         return res.output_text;
//       },
//     };
//   } catch (error) {
//     throw new ProviderError("openai adapter failed to load", error);
//   }
// }

/**
 * 按 config 选 Embedder 实现。默认 mock;未知 provider 显式抛错(不沉默回退)。
 *
 * @param config - 已加载的应用配置。
 * @returns 选定的 Embedder 实现。
 * @throws {ProviderError} provider 未知时。
 */
export function makeEmbedder(config: AppConfig): Embedder {
  const provider = config.server.LLM_PROVIDER;
  if (provider === "mock") {
    return new MockEmbedder();
  }
  // 真实后端按 makeLLM 同款模式(optionalDependencies + 动态 import)接入。
  throw new ProviderError(`unknown embedder provider: ${provider}`);
}
