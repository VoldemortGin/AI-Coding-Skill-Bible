// 冒烟测试:config 默认加载、env 覆盖、Zod 越界拒绝、prompt 严格渲染、缺变量抛错、
// logProvenance 不打印 payload。全部离线、无 key。

import { describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { loadConfig } from "./config.js";
import { readSettingsFile } from "./config-node.js";
import { createLogger, logProvenance } from "./logging.js";
import { PromptError, renderPrompt } from "./prompts.js";
import { loadPrompt, renderNamedPrompt } from "./prompts-node.js";

describe("config", () => {
  it("loads defaults with no file and no env", () => {
    const config = loadConfig({ env: {}, file: {} });
    expect(config.server.LLM_PROVIDER).toBe("mock");
    expect(config.server.RETRIEVER_TOP_K).toBe(5);
    expect(config.server.NODE_ENV).toBe("development");
    expect(config.rerankModel).toBe("mock-rerank");
  });

  it("applies env overrides on top of defaults", () => {
    const config = loadConfig({
      env: { LLM_PROVIDER: "openai", RETRIEVER_TOP_K: "7" },
      file: {},
    });
    expect(config.server.LLM_PROVIDER).toBe("openai");
    expect(config.server.RETRIEVER_TOP_K).toBe(7);
  });

  it("uses file layer when env is absent", () => {
    const config = loadConfig({
      env: {},
      file: { llmProvider: "filey", retriever: { topK: 9, rerankModel: "file-rerank" } },
    });
    expect(config.server.LLM_PROVIDER).toBe("filey");
    expect(config.server.RETRIEVER_TOP_K).toBe(9);
    expect(config.rerankModel).toBe("file-rerank");
  });

  it("rejects out-of-range RETRIEVER_TOP_K", () => {
    expect(() => loadConfig({ env: { RETRIEVER_TOP_K: "0" }, file: {} })).toThrow(z.ZodError);
    expect(() => loadConfig({ env: { RETRIEVER_TOP_K: "101" }, file: {} })).toThrow(z.ZodError);
  });

  it("readSettingsFile returns {} for a missing directory", () => {
    expect(readSettingsFile("/nonexistent/path/for/test")).toEqual({});
  });
});

describe("prompts", () => {
  it("loads a bundled prompt", () => {
    const template = loadPrompt("rag/answer");
    expect(template).toContain("{{ context }}");
    expect(template).toContain("{{ question }}");
  });

  it("renders all placeholders", () => {
    const out = renderPrompt("Hello {{ name }}", { name: "world" });
    expect(out).toBe("Hello world");
  });

  it("throws on a missing variable (strict rendering)", () => {
    expect(() => renderPrompt("Hello {{ name }}", {})).toThrow(PromptError);
  });

  it("loads and renders a named prompt", () => {
    const out = renderNamedPrompt("rag/answer", { context: "ctx", question: "q?" });
    expect(out).toContain("ctx");
    expect(out).toContain("q?");
    expect(out).not.toContain("{{");
  });
});

describe("logging", () => {
  it("redacts sensitive fields and never prints payloads", () => {
    const lines: string[] = [];
    const spy = vi.spyOn(console, "log").mockImplementation((line: unknown) => {
      lines.push(String(line));
    });
    const log = createLogger({ scope: "test" });
    log.info("hi", { apiKey: "sk-secret", count: 3 });
    const line = lines.at(0) ?? "";
    expect(line).not.toContain("sk-secret");
    expect(line).toContain("[REDACTED]");
    spy.mockRestore();
  });

  it("logProvenance emits source/impl/version/count", () => {
    const lines: string[] = [];
    const spy = vi.spyOn(console, "log").mockImplementation((line: unknown) => {
      lines.push(String(line));
    });
    logProvenance({ source: "embedder", impl: "MockEmbedder", version: "1", count: 2 });
    const line = lines.at(0) ?? "";
    expect(line).toContain("provenance");
    expect(line).toContain("MockEmbedder");
    spy.mockRestore();
  });
});
