// provider conformance:任何号称实现了某 port 的类型(Mock 与未来的真实后端)都必须
// 跑过同一组行为不变量 —— 可插拔只在所有插头行为一致时才安全。真实 adapter 在有 key 时
// 追加进数组;默认只测 Mock。另含 factory 装配缝 smoke。

import type { Embedder, LLM } from "@__SCOPE__/domain";
import { ProviderError } from "@__SCOPE__/domain";
import { loadConfig } from "@__SCOPE__/kernel";
import { describe, expect, it } from "vitest";

import { makeEmbedder, makeLLM } from "./factory.js";
import { MockEmbedder, MockLLM } from "./mock.js";

const embedders: { name: string; make: () => Embedder }[] = [
  { name: "MockEmbedder", make: () => new MockEmbedder() },
  // 启用真实后端时追加,例如:{ name: "OpenAIEmbedder", make: () => new OpenAIEmbedder() },
];

const llms: { name: string; make: () => LLM }[] = [{ name: "MockLLM", make: () => new MockLLM() }];

describe.each(embedders)("Embedder conformance: $name", ({ make }) => {
  it("is deterministic (same input → same output)", async () => {
    const embedder = make();
    const first = await embedder.embed(["hello", "world"]);
    const second = await embedder.embed(["hello", "world"]);
    expect(first).toEqual(second);
  });

  it("preserves input count", async () => {
    const vectors = await make().embed(["a", "b", "c"]);
    expect(vectors).toHaveLength(3);
  });

  it("returns non-empty vectors", async () => {
    const vectors = await make().embed(["x"]);
    expect(vectors.every((v) => v.length > 0)).toBe(true);
  });
});

describe.each(llms)("LLM conformance: $name", ({ make }) => {
  it("returns a non-empty completion", async () => {
    const output = await make().complete("ping");
    expect(output.length).toBeGreaterThan(0);
  });
});

describe("factory (composition seam)", () => {
  it("defaults to mock and runs end to end without a key", async () => {
    const config = loadConfig({ env: {}, file: {} });
    const llm = await makeLLM(config);
    const embedder = makeEmbedder(config);

    const answer = await llm.complete("ping");
    expect(answer.startsWith("[mock]")).toBe(true);

    const vectors = await embedder.embed(["a", "b"]);
    expect(vectors).toHaveLength(2);
  });

  it("rejects an unknown provider (no silent fallback)", async () => {
    const config = loadConfig({ env: { LLM_PROVIDER: "nope" }, file: {} });
    await expect(makeLLM(config)).rejects.toBeInstanceOf(ProviderError);
    expect(() => makeEmbedder(config)).toThrow(ProviderError);
  });
});
