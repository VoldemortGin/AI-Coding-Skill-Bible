import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// React + Vite 薄壳。`?raw` import 可把 kernel 的 `.md` 提示词作字符串内联到 bundle
// (浏览器侧不走 node fs;见 App.tsx)。
export default defineConfig({
  plugins: [react()],
});
