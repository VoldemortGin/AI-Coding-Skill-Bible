# __SCOPE__ — AI 开发约束(常驻,根级路由表)

> 只放硬约束 + 去哪找。**每个 package / app 有自己的 `CLAUDE.md`**(就近契约),领域细节不在此堆叠。

## 不可违反(违反即破坏设计)

- TypeScript `strict` + 更严 flags(`tsconfig.base.json`):`noUncheckedIndexedAccess` / `exactOptionalPropertyTypes` / `noImplicitOverride` / `noImplicitReturns` / `noFallthroughCasesInSwitch` / `noPropertyAccessFromIndexSignature` / `allowUnreachableCode:false` / `verbatimModuleSyntax` / `isolatedModules`。`tsc --noEmit` 是静态门的核心。
- 关死逃生舱:禁 `any`(`no-explicit-any` + `no-unsafe-*`)、禁非空 `!`(`no-non-null-assertion`)、`@ts-ignore` 一律改 `@ts-expect-error -- 原因`、`as` 尽量少且写理由。逃生须显式、可审计、可 grep:`// eslint-disable-next-line <rule> -- 原因`。
- 运行时擦除 → **Zod 在每个边界 parse**:fetch/API 响应、表单、`env`、`localStorage`、URL/search params、postMessage、LLM 输出。`z.infer` 出类型,非法即抛(parse, don't validate)。
- 不静默失败:不留空 `catch {}`(处理或重抛);穷尽 `switch`(`switch-exhaustiveness-check` + `never` 兜底);Promise 不悬空(`no-floating-promises`);边界外错误归一到 `ProviderError`。
- 框架无关核心:`packages/{kernel,domain,adapters,<domain>}` 零 React / 零 Next;只有 `apps/*` 碰框架。`domain` 包 **零 SDK 且零 UI 框架依赖**(解析 package.json 机械检查)。
- 外部 AI 依赖只经 `@__SCOPE__/domain` 的 interface;厂商 SDK 只在 `@__SCOPE__/adapters`(optionalDependencies + 动态 `await import()`);默认 `MockProvider` 离线、无 key、零 SDK。
- 完成 = 一条门绿:`./ci.sh`(tsc → eslint `--max-warnings 0` → prettier --check → vitest → turbo build 两壳)。唯一判据,不许"看着没问题就提交"。
- 结构 package-per-domain;命名即定位。依赖方向:领域包 / `adapters` → `domain` + `kernel`;`apps/*` → 全部(composition root)。

## 流程

- 方向先写 `docs/adr/`(编号、不可变:背景 + 选定 + 被否决备选及理由)再编码。
- TDD:先写会失败的测试(vitest),再实现到绿,绝不弱化测试。
- 大改拆编号步骤,每步过 `./ci.sh` 再下一步,不攒巨 diff。
- 写完另起独立、带敌意的复审(假设有错去证伪),优先审测试盖不到的取舍。

## 去哪找

- 完整标准与 rationale:skill 的 `references/standard.md`。
- 各包契约:`packages/<name>/CLAUDE.md`、`apps/<name>/CLAUDE.md`。
- 实现层怎么写(本标准不复述,委托引用):
  - React 组件性能:`react-best-practices`;组件组合 / UI 级 DI:`composition-patterns`;React 19:`react-expert`。
  - Next App Router 机制:`nextjs-developer` / `nextjs-app-router-fundamentals` / `nextjs-server-client-components`。
  - 视觉 / 设计:`frontend-design` / `design-taste-frontend` / `impeccable`。
  - E2E 测试:`webapp-testing`(Playwright)。
