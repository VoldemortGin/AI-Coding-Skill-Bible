// 入口:挂载 React 树。composition root 在 App.tsx。

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App.js";

const container = document.getElementById("root");
if (container === null) {
  throw new Error("#root not found");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
