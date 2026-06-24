// node 专属:加载随 kernel 包出厂的 `.md` 提示词。浏览器侧绝不 import 本模块。
//
// `new URL('./prompts/...', import.meta.url)` 按相对自身的 URL 定位(无运行时 cwd 问题,
// 供 vitest / CLI)。package.json `files` 含 `src/prompts`,提示词随包出厂。

import { readFileSync } from "node:fs";

import { PromptError, renderPrompt } from "./prompts.js";

/**
 * 加载随包出厂的提示词原始文本(node 环境)。
 *
 * @param name - 相对 `prompts/` 的子路径(不含 `.md`),如 `rag/answer`。
 * @returns 模板原始文本。
 * @throws {PromptError} 资源不存在 / 读取失败时抛出。
 */
export function loadPrompt(name: string): string {
  const url = new URL(`./prompts/${name}.md`, import.meta.url);
  try {
    return readFileSync(url, "utf8");
  } catch (error) {
    throw new PromptError(`prompt not found: ${name} (${String(error)})`);
  }
}

/**
 * 便捷:加载并严格渲染一个随包出厂的提示词。
 *
 * @param name - 提示词子路径(不含 `.md`)。
 * @param variables - 变量字典。
 * @returns 渲染后的文本。
 * @throws {PromptError} 资源缺失或变量缺失时抛出。
 */
export function renderNamedPrompt(name: string, variables: Record<string, string>): string {
  return renderPrompt(loadPrompt(name), variables);
}
