// kernel node 专属入口(`@__SCOPE__/kernel/node`):依赖 node 内置的能力。
// 浏览器 bundle 绝不 import 本入口。

export { readSettingsFile } from "./config-node.js";
export { loadPrompt, renderNamedPrompt } from "./prompts-node.js";
