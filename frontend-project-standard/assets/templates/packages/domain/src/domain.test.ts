// 冒烟测试:Zod 边界模型的越界拒绝 / 合法通过,错误类型的形状。

import { describe, expect, it } from "vitest";

import { Document, TopK } from "./models.js";
import { DomainError, ProviderError } from "./errors.js";

describe("models", () => {
  it("TopK accepts values in 1..100", () => {
    expect(TopK.parse(1)).toBe(1);
    expect(TopK.parse(100)).toBe(100);
  });

  it("TopK rejects out-of-range and non-integer values", () => {
    expect(() => TopK.parse(0)).toThrow();
    expect(() => TopK.parse(101)).toThrow();
    expect(() => TopK.parse(1.5)).toThrow();
  });

  it("Document parses a valid record", () => {
    const doc = Document.parse({ id: "a", text: "hello" });
    expect(doc.id).toBe("a");
    expect(doc.text).toBe("hello");
  });

  it("Document rejects an empty id", () => {
    expect(() => Document.parse({ id: "", text: "x" })).toThrow();
  });
});

describe("errors", () => {
  it("ProviderError carries name and optional cause", () => {
    const err = new ProviderError("boom", new Error("root"));
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe("ProviderError");
    expect(err.cause).toBeInstanceOf(Error);
  });

  it("DomainError carries name", () => {
    const err = new DomainError("bad");
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe("DomainError");
  });
});
