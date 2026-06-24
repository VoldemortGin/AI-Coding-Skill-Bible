// @ts-check
// 共享 flat config:类型感知 lint 是静态门的一半(另一半是 tsc --noEmit)。
// typescript-eslint `strictTypeChecked` + `stylisticTypeChecked` + `projectService`,
// 关死逃生舱(any / 非空 ! / 裸 @ts-ignore / 危险 as),不静默失败(悬空 Promise、
// 非穷尽 switch),末尾 `eslint-config-prettier` 解除与 Prettier 冲突的格式规则。

import js from "@eslint/js";
import eslintConfigPrettier from "eslint-config-prettier";
import tseslint from "typescript-eslint";

export default tseslint.config(
  // 忽略产物与配置脚本(等价 .eslintignore)。
  {
    ignores: [
      "**/dist/**",
      "**/.next/**",
      "**/.turbo/**",
      "**/coverage/**",
      "**/node_modules/**",
      "**/next-env.d.ts",
    ],
  },

  // 类型感知主配置,作用于所有 TS/TSX 源码。
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.strictTypeChecked,
      ...tseslint.configs.stylisticTypeChecked,
    ],
    languageOptions: {
      parserOptions: {
        // projectService 自动按最近的 tsconfig 提供类型信息(无需手列 project 数组)。
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      // —— 关死逃生舱(§4)——
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unsafe-assignment": "error",
      "@typescript-eslint/no-unsafe-call": "error",
      "@typescript-eslint/no-unsafe-member-access": "error",
      "@typescript-eslint/no-unsafe-return": "error",
      "@typescript-eslint/no-unsafe-argument": "error",
      "@typescript-eslint/no-non-null-assertion": "error",
      // @ts-ignore 禁用;@ts-expect-error 必须带说明(可审计、可 grep)。
      "@typescript-eslint/ban-ts-comment": [
        "error",
        {
          "ts-ignore": true,
          "ts-expect-error": { descriptionFormat: "^ -- .+$" },
        },
      ],

      // —— 不静默失败(§4)——
      "@typescript-eslint/no-floating-promises": "error",
      "@typescript-eslint/no-misused-promises": "error",
      "@typescript-eslint/switch-exhaustiveness-check": "error",

      // —— 一致的 type-only import(verbatimModuleSyntax 要求)——
      "@typescript-eslint/consistent-type-imports": "error",
    },
  },

  // 测试文件:沿用同一套严格规则,无需放宽。

  // 必须放最后:关掉所有与 Prettier 冲突的格式化规则。
  eslintConfigPrettier,
);
