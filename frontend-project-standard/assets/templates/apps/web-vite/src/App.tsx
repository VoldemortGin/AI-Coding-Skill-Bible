// composition root(React + Vite 薄壳):加载 kernel config(浏览器侧主入口,不碰 node)、
// 用 adapters 的 MockLLM/MockEmbedder 调一次、用 `?raw` 内联的提示词严格渲染、渲染结果到页面。
//
// 框架只在 apps/* 出现;领域 / 装配逻辑全在框架无关的 packages/*。组件 / 视觉细节
// 委托 react-best-practices / composition-patterns / frontend-design 等 skill,本壳保持极薄。

import { useEffect, useState } from "react";

import { makeEmbedder, makeLLM } from "@__SCOPE__/adapters";
import { loadConfig, logProvenance, PromptError, renderPrompt } from "@__SCOPE__/kernel";
// bundler 侧:用 `?raw` 把随 kernel 出厂的 .md 提示词作字符串内联(浏览器不走 node fs)。
import answerTemplate from "@__SCOPE__/kernel/prompts/rag/answer.md?raw";

interface DemoResult {
  readonly provider: string;
  readonly answer: string;
  readonly vectorCount: number;
}

async function runDemo(): Promise<DemoResult> {
  // 浏览器侧:env 来自 import.meta.env(VITE_ 前缀);file 层留空(不读 fs)。
  // import.meta.env 的索引签名是 any,先窄化为 string 再用(关死 unsafe 逃生舱)。
  const rawAppName: unknown = import.meta.env["VITE_APP_NAME"];
  const appName = typeof rawAppName === "string" ? rawAppName : "vite-app";
  const config = loadConfig({
    env: { NEXT_PUBLIC_APP_NAME: appName },
    file: {},
  });

  const llm = await makeLLM(config);
  const embedder = makeEmbedder(config);

  const vectors = await embedder.embed(["Vite ships ESM to the browser with instant HMR."]);
  logProvenance({ source: "embedder", impl: "MockEmbedder", version: "1", count: vectors.length });

  const prompt = renderPrompt(answerTemplate, {
    context: "Vite serves source over native ESM and bundles with Rollup for production.",
    question: "How does Vite serve source during development?",
  });
  const answer = await llm.complete(prompt);

  return { provider: config.server.LLM_PROVIDER, answer, vectorCount: vectors.length };
}

export function App(): React.JSX.Element {
  const [result, setResult] = useState<DemoResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    runDemo()
      .then(setResult)
      .catch((err: unknown) => {
        // 不静默吞:把边界错误显式呈现。
        setError(err instanceof PromptError ? `prompt: ${err.message}` : String(err));
      });
  }, []);

  if (error !== null) {
    return <main>Error: {error}</main>;
  }
  if (result === null) {
    return <main>Loading…</main>;
  }
  return (
    <main>
      <h1>__SCOPE__ · web-vite</h1>
      <p>provider: {result.provider}</p>
      <p>vectors: {result.vectorCount}</p>
      <pre>{result.answer}</pre>
    </main>
  );
}
