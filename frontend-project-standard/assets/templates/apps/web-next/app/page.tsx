// composition root(Next.js App Router 薄壳):server component。加载 kernel config、
// node 侧用 readSettingsFile 读文件层 + renderNamedPrompt 加载随包出厂的提示词、
// 用 adapters 的 MockLLM/MockEmbedder 调一次、渲染结果。
//
// 框架只在 apps/* 出现;领域 / 装配逻辑全在框架无关的 packages/*。Next 机制(server/client
// component、route handler、streaming 等)委托 nextjs-developer / nextjs-app-router-fundamentals
// 等 skill,本壳保持极薄。

import { makeEmbedder, makeLLM } from "@__SCOPE__/adapters";
import { loadConfig, logProvenance } from "@__SCOPE__/kernel";
import { readSettingsFile, renderNamedPrompt } from "@__SCOPE__/kernel/node";

export default async function Page(): Promise<React.JSX.Element> {
  // server component:可安全读 server env + 文件层(node)。
  const config = loadConfig({ file: readSettingsFile() });

  const llm = await makeLLM(config);
  const embedder = makeEmbedder(config);

  const vectors = await embedder.embed([
    "Next.js App Router renders Server Components by default.",
  ]);
  logProvenance({ source: "embedder", impl: "MockEmbedder", version: "1", count: vectors.length });

  const prompt = renderNamedPrompt("rag/answer", {
    context: "Next.js App Router runs Server Components on the server by default.",
    question: "Where do Next.js App Router components run by default?",
  });
  const answer = await llm.complete(prompt);

  return (
    <main>
      <h1>__SCOPE__ · web-next</h1>
      <p>provider: {config.server.LLM_PROVIDER}</p>
      <p>vectors: {vectors.length}</p>
      <pre>{answer}</pre>
    </main>
  );
}
