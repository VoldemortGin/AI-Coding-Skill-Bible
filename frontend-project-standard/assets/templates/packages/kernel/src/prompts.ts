// [AI 层] 提示词渲染(浏览器安全:不 import node 内置)。
//
// 严格渲染:模板出现但未提供的 `{{ var }}` 直接抛 ``PromptError``(对应 StrictUndefined),
// 而非静默留空。模板语法极简:`{{ name }}` 占位。
//
// 加载随包出厂的 `.md`:node 侧用 `@__SCOPE__/kernel/node` 的 `loadPrompt`
// (`fs.readFileSync(new URL(..., import.meta.url))`);bundler 侧用 `?raw` import
// 把 `.md` 作为字符串内联,再交给这里的 `renderPrompt`。

/** 提示词错误。 */
export class PromptError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PromptError";
  }
}

/**
 * 严格渲染:`{{ key }}` 全部替换;模板引用了未提供的变量即抛错。
 *
 * @param template - 含 `{{ key }}` 占位的模板文本。
 * @param variables - 变量字典。
 * @returns 所有占位符替换后的文本。
 * @throws {PromptError} 模板引用了 `variables` 中不存在的变量。
 */
export function renderPrompt(template: string, variables: Record<string, string>): string {
  return template.replace(/\{\{\s*([\w.]+)\s*\}\}/g, (_match, rawKey: string) => {
    const key = rawKey.trim();
    const value = variables[key];
    if (value === undefined) {
      throw new PromptError(`missing variable: ${key}`);
    }
    return value;
  });
}
