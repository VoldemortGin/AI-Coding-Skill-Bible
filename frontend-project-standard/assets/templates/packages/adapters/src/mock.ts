// 确定性离线默认实现(default,不是测试桩):不联网、无需 key 也能跑通并通过测试;
// 同输入同输出,不被随机性污染。这是组装根的默认选择。零 SDK。

import type { Embedder, LLM } from "@__SCOPE__/domain";

/** 确定性 mock LLM:回显被截断的 prompt 头部。 */
export class MockLLM implements LLM {
  complete(prompt: string): Promise<string> {
    const head = prompt.slice(0, 40);
    return Promise.resolve(`[mock] ${head}`);
  }
}

/** 确定性 mock embedder(同输入同输出,保持数量)。 */
export class MockEmbedder implements Embedder {
  embed(texts: string[]): Promise<number[][]> {
    const vectors = texts.map((text) => {
      let sum = 0;
      for (const ch of text) {
        sum += ch.codePointAt(0) ?? 0;
      }
      return [(sum % 1000) / 1000];
    });
    return Promise.resolve(vectors);
  }
}
