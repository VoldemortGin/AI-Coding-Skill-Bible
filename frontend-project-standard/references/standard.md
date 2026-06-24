# 前端项目标准(完整版)

面向 AI 主导开发的 TypeScript 前端工程标准。与 Python / Swift / Rust 姊妹标准同一条脊:**信任放在可被机器检验的代码上,而非模型。** 前端与 **Python 最像**:TypeScript 在编写期是强类型,但**类型在运行时被擦除**——编译器证明过是 `User` 的对象,运行起来只是个普通 object;一个标了 `as Product[]` 的 `fetch` 响应,实际是服务端真正发回来的任何东西。所以前端需要**两层**,精确对应 Python 姊妹标准的 mypy + pydantic:**`tsc` strict 给静态保证,Zod 在边界给运行时保证,二者缺一不可**。

> **与 Python 的关键差异**:Python 的 beartype 用 import-hook 给**进程内每个调用点**装运行时类型检查;前端在浏览器/Node 里**没有这种 import-hook**,逐调用点插桩不存在。所以运行时这一层**只集中在边界**(§3):静态门覆盖内部,Zod 覆盖一切跨进来的值。这是前端唯一一处偏离 Python 的地方,其余(双层类型、零警告门、关死逃生舱、模型无关缝、命名即路径、隐性兜底外化)逐项对齐。

> **定位**:本标准是**项目级工程标准(总纲 + 工程门 + 架构约定)**。"实现层怎么写"——组件性能、组合模式、React 19、Next App Router 机制、视觉审美、E2E——委托引用已有 skill,本文在相关处指引"详见 …",不重写其内容:
>
> - 组件性能 / memo / 渲染纪律 → `react-best-practices`
> - 组件组合 / compound component / render props / UI 级依赖注入 → `composition-patterns`
> - React 19 API(`use`、actions、`useOptimistic`、ref-as-prop) → `react-expert`
> - Next.js App Router 机制(server/client component、server actions、路由、streaming) → `nextjs-developer` 及 `nextjs-*` 族
> - 视觉 / 审美 / 设计系统 → `frontend-design` / `design-taste-frontend` / `impeccable`
> - 端到端浏览器测试 → `webapp-testing`(Playwright)

**适用范围(分两层)**:下列约束分为**通用脊**与**AI 触发层**。

- **通用脊**(任何前端项目都适用,与是否碰 AI 无关):TypeScript `strict` + 更严 flags、零警告门(tsc + eslint + prettier + vitest + build)、不静默失败、Zod 边界校验、pnpm + Turborepo package-per-domain + 深命名、结构化日志、Zod 校验 env、类型感知 ESLint + Prettier。
- **AI 触发层**(只在项目真的调用 LLM / embedding / 向量库时启用):`domain` 接口缝 + 零-SDK 零框架 domain 包、`MockProvider` 作默认、bundled prompts + 严格渲染、`logProvenance`、约束下沉控制流。

纯展示站 / 营销页 / 仪表盘等不碰模型的项目应全量采用通用脊、整层跳过 AI 层;在那种项目里硬套 `MockProvider` 或提示词嵌入是 cargo-cult,不是合规。

基线:Node 22+、**pnpm** workspace + **Turborepo**、ES modules(`"type": "module"`)、最新稳定 **TypeScript**(`tsconfig.base.json` 严格基线被所有包 extends)、**Zod**(边界 + env)、**ESLint** flat config + **typescript-eslint** 类型感知(`strictTypeChecked` + `stylisticTypeChecked`,`projectService: true`)+ **Prettier**、**Vitest**、两个薄壳(**React + Vite** 的 `apps/web-vite` 与 **Next.js App Router** 的 `apps/web-next`)。TS-first:`src/` 不出现 `.js`,仅工具配置在硬要求处容忍 `.mjs`/`.cjs`。

---

## 1. 唯一的零警告门(完成的唯一判据)

`ci.sh` 一条 `set -euo pipefail` 脚本,人和 agent 共用,按"快→慢"排,让 agent 尽早拿到反馈:

```bash
#!/usr/bin/env bash
set -euo pipefail
pnpm install --frozen-lockfile
pnpm turbo run typecheck       # tsc --noEmit(各包,静态全分支)
pnpm turbo run lint            # eslint --max-warnings 0(类型感知 lint)
pnpm run format:check          # prettier --check .
pnpm turbo run test            # vitest run(各包,含 smoke + conformance)
pnpm turbo run build           # 两壳 + 包构建
```

任一项非零即没完成。根 `package.json` 提供 `typecheck/lint/test/build/format:check` 脚本;各包 `package.json` 提供自身 `typecheck/lint/test/build`,由 Turbo 按依赖图(`turbo.json` 的 `dependsOn`)缓存 + 拓扑并行。`--max-warnings 0` 是关键:它把 ESLint 的一切告警提升为致命,等价于其他语言的 warnings-as-errors。`prettier --check` 只读不写,差异即非零。用 pre-push hook 钉死;CI 镜像同一套。

这是 agent 唯一的正确性判据,不允许"看起来没问题就提交",也**禁止**用零散的、需人工判读的检查替代——必须收敛到这一条命令,改一次跑一次,解析机器可读错误,修复,重复到全绿。

---

## 2. 静态门:TypeScript `strict` + 更严 flags,逃生舱关死

TS 类型在编写期由 `tsc` 强制(全分支、不运行),这是 mypy `--strict` 的对应。"最严、无逃生舱"分两半:严 flags 拉满 + 逃生舱关死。

### 2.1 `tsconfig.base.json` —— 静态门的核心

被所有包 `extends`。下列严格 flag 不得删(agent 可按编译实际微调 `module`/`moduleResolution` 让 monorepo 跑通,但严 flag 不动):

```jsonc
{
  "compilerOptions": {
    "strict": true,                              // 总开关:strictNullChecks 等全开
    "noUncheckedIndexedAccess": true,            // arr[i] / obj[k] 类型带 undefined,逼你处理越界/缺键
    "exactOptionalPropertyTypes": true,          // { x?: T } 不等于 { x: T | undefined };禁止把显式 undefined 塞进可选字段
    "noImplicitOverride": true,                  // 覆写父类成员必须写 override,签名漂移即暴露
    "noImplicitReturns": true,                   // 有的分支 return 有的不 return → 报错
    "noFallthroughCasesInSwitch": true,          // case 漏 break 贯穿 → 报错(配合 §4 穷尽 switch)
    "noPropertyAccessFromIndexSignature": true,  // 索引签名只能用 obj["k"] 而非 obj.k,把"动态键"与"已知属性"分开
    "allowUnreachableCode": false,               // 死代码即错误
    "verbatimModuleSyntax": true,                // import type / import 语义精确,配合 isolatedModules 让单文件转译安全
    "isolatedModules": true,                     // 每个文件可独立转译(Vite/esbuild/swc 的前提)
    "forceConsistentCasingInFileNames": true,    // 跨平台大小写一致(macOS/Windows 不敏感,Linux 敏感)
    "skipLibCheck": true,                         // 跳过 .d.ts 内部检查,加速;自己的代码仍全检
    "noEmit": true                                // 仅 typecheck;构建由 vite/next/tsc 各包负责
  }
}
```

**为何要这几个超出 `strict` 的 flag**:`strict` 只是一组基础开关的集合,真正容易藏 bug 的是 `strict` *没有*覆盖的几个:

- `noUncheckedIndexedAccess` —— 最值钱的一个。`const x = arr[0]` 在没它时类型是 `T`(谎言),有它时是 `T | undefined`(真相),逼你处理"取不到"——前端到处是 `params[id]`、`record[key]`、`array[index]`,这一项把最常见的 `undefined is not an object` 提前到编译期。
- `exactOptionalPropertyTypes` —— 让"字段不存在"与"字段是 undefined"在类型上可区分,避免 React props / 配置对象里 `{ value: undefined }` 被当成"没传"。
- `noImplicitOverride` / `noImplicitReturns` / `noFallthroughCasesInSwitch` —— 把签名漂移、漏 return、switch 贯穿这三类静默错误变成编译错误。
- `noPropertyAccessFromIndexSignature` —— 把"我确定有这个属性"和"我在按动态键取"分开,防止打错属性名却因索引签名被静默放行。

### 2.2 逃生舱一律关死(由类型感知 ESLint 钉死)

TS 的逃生舱不像 Swift 的 `!` 那样是语法关键字,而是散落的几种"放弃类型检查"的写法。`eslint.config.mjs` 用 **typescript-eslint 类型感知规则**(`projectService: true`,需要类型信息才能抓 `no-unsafe-*`)把它们关死:

```js
// eslint.config.mjs(节选,flat config)
import tseslint from 'typescript-eslint';
import eslintConfigPrettier from 'eslint-config-prettier';

export default tseslint.config(
  ...tseslint.configs.strictTypeChecked,       // 含 no-explicit-any / no-unsafe-* / no-floating-promises 等
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: { parserOptions: { projectService: true } },
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',           // 禁 any
      '@typescript-eslint/no-non-null-assertion': 'error',     // 禁 foo!
      '@typescript-eslint/ban-ts-comment': [                    // @ts-ignore 禁;@ts-expect-error 须带说明
        'error',
        { 'ts-ignore': true, 'ts-expect-error': 'allow-with-description' },
      ],
      '@typescript-eslint/no-floating-promises': 'error',       // §4
      '@typescript-eslint/no-misused-promises': 'error',        // §4
      '@typescript-eslint/switch-exhaustiveness-check': 'error',// §4
      '@typescript-eslint/consistent-type-imports': 'error',    // 配合 verbatimModuleSyntax
      // no-unsafe-assignment / -call / -member-access / -return / -argument 由 strictTypeChecked 开为 error
    },
  },
  eslintConfigPrettier,                          // 必须最后:关掉所有与 Prettier 冲突的格式规则
);
```

逐条对应:

- **`any`** —— 禁(`no-explicit-any` + `no-unsafe-*` 一族)。需要动态时用 `unknown` + 收窄(类型守卫 / Zod parse),或 `Record<string, unknown>`、联合、泛型。`any` 会沿调用链"传染"地关掉检查,`no-unsafe-*` 正是抓这种传染。
- **非空断言 `!`** —— 禁(`no-non-null-assertion`)。`foo!.bar` 是在对编译器撒谎"这肯定不是 null"。用 `if (foo)` / `foo?.bar` / `??` / `assert`(抛错的运行时断言)显式处理。
- **`@ts-ignore`** —— 禁,必须改用 **`@ts-expect-error -- 原因`**(`ban-ts-comment`)。区别关键:`@ts-expect-error` 在下一行**没有错误时它自己会报错**——所以当依赖升级、bug 修好后,这个豁免会主动提醒你删掉,不会变成永久的沉默债务(`@ts-ignore` 不会)。
- **`as` 断言** —— 软逃生舱。`as` 本身不被一刀切禁(`satisfies`、`as const`、收窄后的 `as` 是合法用法),但**危险的 `as`**(把 `unknown`/`any` 强转成具体类型、跨不兼容类型转)由 `no-unsafe-*` 抓住。标准要求:尽量少用,跨边界的数据**不要 `as`,要 Zod parse**(§3);确需断言时优先 `satisfies`(只校验不放宽)。

### 2.3 受控出口

个别站点确需逃生(框架契约、第三方 `.d.ts` 缺陷、编译期已知合法),不在全局松绑,而是**逐处显式豁免并写理由**:

```ts
// eslint-disable-next-line @typescript-eslint/no-non-null-assertion -- root 元素由 index.html 保证存在
const root = document.getElementById('root')!;

// @ts-expect-error -- 第三方 @types/foo 漏标了 v3 的 options 参数,已提 issue #123
foo.configure({ strict: true });
```

这是 Python `# type: ignore[code] # 原因` / Swift `// swiftlint:disable:next force_unwrapping — 原因` / Rust `#[allow(clippy::...)] // 原因` 的前端等价物:不是禁止,是让每次逃生**显式、可审计、可 grep**。`@ts-expect-error` 还自带"失效即报错"的反债务机制。

---

## 3. 运行时边界:parse, don't validate —— Zod

**为什么运行时校验在前端是必需的**:TS 类型在 `tsc` 跑完后**全部擦除**,运行时一行类型代码都不剩。这意味着任何**从程序外部进来的值**——你没法在编译期看到的真实数据——在被 parse 之前都是不可信的,即使你给它标了类型。最典型的谎言:

```ts
// ❌ 这行没有任何运行时保证。服务端发回什么,products 就是什么;
//    类型只是"我希望它是 Product[]",运行时它可能是 { error: "..." }。
const products = (await res.json()) as Product[];
```

这正是 Python 用 pydantic、Rust 用 serde + newtype、Swift 用 Codable + newtype 在边界做的事;前端用 **Zod**。规则是 **parse, don't validate**:在入口处把外部值 parse 成强类型值,**schema 是唯一事实来源**,用 `z.infer` 反推静态类型,非法即在边界抛错——而不是先 `as` 放进来、再在三层之外炸。

```ts
import { z } from 'zod';

// 1. schema 是唯一事实来源
const ProductSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  priceCents: z.number().int().nonnegative(),
  tags: z.array(z.string()).default([]),
});

// 2. 静态类型由 schema 反推,不重复声明(改 schema 自动改类型)
type Product = z.infer<typeof ProductSchema>;

// 3. 在边界 parse,而非信任
async function fetchProducts(): Promise<Product[]> {
  const res = await fetch('/api/products');
  if (!res.ok) throw new ProviderError(`products ${res.status}`);
  const raw: unknown = await res.json(); // 注意:json() 返回 unknown,不是 any
  return z.array(ProductSchema).parse(raw); // 非法即抛,带精确路径
}
```

需要"校验失败不抛、走分支处理"时用 `safeParse`:

```ts
const result = LLMToolCallSchema.safeParse(rawFromModel);
if (!result.success) {
  // result.error.issues 是机器可读的逐字段错误(path + message + code)
  logger.warn('llm output failed schema', { issues: result.error.issues });
  return { kind: 'unrecognized' as const }; // 收窄发射面:坏输出归一成已知态,不渗进下游
}
const call = result.data; // 此处 call 已是强类型且已校验
```

**所有边界都要 parse,不只是 fetch**:

- `fetch` / API 响应、第三方 webhook 载荷
- 表单输入(配合 `react-hook-form` 的 zod resolver)
- `env`(§5)
- `localStorage` / `sessionStorage`(存的是字符串,读回来 `JSON.parse` 后是 `unknown`)
- URL / search params(`URLSearchParams` 全是 `string | null`)
- `postMessage` / `BroadcastChannel`
- **LLM 输出**(模型返回的"结构化 JSON"最不可信,§9 的 conformance 也靠它)

> **Zod vs TS 决策规则**(对应 Python 的 pydantic vs beartype):**跨进程/网络/存储边界进来的值 → Zod parse**(需要校验合法性,常要转换/收窄/给默认值);**进程内部的契约 → 直接靠 TS 类型**(数据已在掌控内,编译期已保证形状)。前端没有 beartype 式的内部运行时断言层,所以内部就只靠静态门——这也是为什么静态门的严 flags(§2.1)在前端格外重要。

---

## 4. 不静默失败

让错误响亮且定位明确,优先于静默地做错事。四个机械点 + 一条边界纪律:

### 4.1 不吞 catch

```ts
// ❌ 空 catch:错误消失,程序带着坏状态继续跑
try { await save(); } catch {}

// ✅ 要么处理(归一 + 上报),要么重抛
try {
  await save();
} catch (err) {
  if (err instanceof ProviderError) {
    logger.error('save failed', { code: err.code });
    throw err; // 不静默:让上层 error boundary / 调用方知道
  }
  throw err; // 未知错(可能是程序 bug)照常上抛,绝不吞进降级路径
}
```

`catch` 的参数在 strict 下是 `unknown`,必须先收窄(`instanceof` / Zod)才能用——这本身就逼你区分"已知的可恢复错"与"未知错"。

### 4.2 穷尽 switch + `never` 兜底

```ts
type Shape =
  | { kind: 'circle'; r: number }
  | { kind: 'rect'; w: number; h: number };

function area(s: Shape): number {
  switch (s.kind) {
    case 'circle': return Math.PI * s.r ** 2;
    case 'rect': return s.w * s.h;
    default: {
      // 若将来给 Shape 加了新成员却忘了在这里处理,下面这行会编译报错:
      // "Type '{ kind: "triangle"; ... }' is not assignable to type 'never'"
      const _exhaustive: never = s;
      throw new Error(`unhandled shape: ${String(_exhaustive)}`);
    }
  }
}
```

`switch-exhaustiveness-check`(ESLint)+ `never` 兜底 + `noFallthroughCasesInSwitch`(§2.1)三重保证:加了新 case 忘处理 = 编译/lint 红。这是 Swift 穷尽 `switch`、Rust `match` 穷尽性的前端等价物。

### 4.3 Promise 不悬空

`no-floating-promises`:每个 Promise 必须被 `await`、`.catch()`、或显式 `void`(明确表示"故意不等")。`no-misused-promises`:禁止把 async 函数传给期望返回 `void` 的位置(如 `onClick={async () => …}` 里未处理 rejection)。悬空 Promise 的 rejection 会变成静默的 unhandled rejection——正是"静默失败"。

### 4.4 React error boundary

app 壳挂一个 error boundary,把渲染期抛出的错误兜成一个可见的降级 UI + 一条结构化日志,而不是白屏 + 控制台一行红字。(Next App Router 用 `error.tsx`;实现细节见 `nextjs-developer`。)

### 4.5 边界错误归一 `ProviderError`

厂商 / 网络 / 超时 / API 错在 **adapter 边界**归一到 `ProviderError`(§9);**程序 bug**(逻辑错、违反不变量)照常上抛或交给 error boundary,**绝不**塞进降级路径吞掉。这与 Python"程序错照常上抛、外部错归一"、Swift/Rust 一致。

---

## 5. 配置:Zod 校验的 env(t3-env 模式)

env 是边界(§3),所以也要 parse。采用 **t3-env 模式**:server env 与 client env 各一个 schema,在启动时 parse `process.env` / `import.meta.env`,**失败即崩**(早崩好过运行到一半因 `undefined` 配置出诡异行为)。优先级:**分层默认 < `configs/settings.json` < env**。

```ts
// packages/kernel/src/config.ts
import { z } from 'zod';

// server-only:绝不暴露给浏览器 bundle
const ServerEnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  OPENAI_API_KEY: z.string().min(1).optional(), // secret 只来自 env
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
});

// client:只有这些会进 bundle。约定必须带 PUBLIC_ 前缀(Vite: VITE_ / Next: NEXT_PUBLIC_)
const ClientEnvSchema = z.object({
  PUBLIC_API_BASE_URL: z.string().url(),
});

function parseEnv<T extends z.ZodTypeAny>(schema: T, source: Record<string, unknown>): z.infer<T> {
  const parsed = schema.safeParse(source);
  if (!parsed.success) {
    // 启动期就把缺失/非法的 env 名字打出来,然后崩
    console.error('❌ invalid environment variables:', parsed.error.flatten().fieldErrors);
    throw new Error('invalid environment variables');
  }
  return parsed.data;
}

// server 入口(Node / Next server component / API route)调用
export const serverEnv = parseEnv(ServerEnvSchema, process.env);

// client 入口调用(Vite 用 import.meta.env;Next 用 process.env 但只读 NEXT_PUBLIC_*)
// export const clientEnv = parseEnv(ClientEnvSchema, import.meta.env);
```

非 env 的**结构化非密配置**(可被 env 逐项覆盖)放根级 `configs/settings.json`,由 kernel 读取并合并:默认值 < `settings.json` < env。其与 prompts(随包出厂,§7)正相反:`settings.json` 环境相关、不入 bundle。

**secret 纪律**:secret(API key 等)**只来自 server env**,绝不写进 `configs/settings.json`、绝不进 client schema、绝不进 bundle(client schema 里出现 secret 字段 = 泄露到浏览器)、绝不落日志(§6 红化)。Vite 把 `import.meta.env.VITE_*` 静态内联进 client bundle,Next 把 `NEXT_PUBLIC_*` 内联——所以**前缀即可见性边界**,server secret 永远不带这些前缀。

---

## 6. 日志 / 血缘 / 隐私:结构化 logger,载荷不落盘

`packages/kernel/src/logging.ts`:统一的结构化 logger(分级、JSON 输出、敏感字段红化)。浏览器与 Node 双端安全(浏览器回退到 `console`,Node 可选 `pino` 作进阶)。

```ts
// packages/kernel/src/logging.ts
type Level = 'debug' | 'info' | 'warn' | 'error';
const ORDER: Record<Level, number> = { debug: 0, info: 1, warn: 2, error: 3 };

// 红化:这些键即使被传进来也不落日志
const SENSITIVE = new Set(['apiKey', 'password', 'token', 'authorization', 'prompt', 'answer']);

function redact(fields: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(fields)) {
    out[k] = SENSITIVE.has(k) ? '[REDACTED]' : v;
  }
  return out;
}

export interface Logger {
  debug(msg: string, fields?: Record<string, unknown>): void;
  info(msg: string, fields?: Record<string, unknown>): void;
  warn(msg: string, fields?: Record<string, unknown>): void;
  error(msg: string, fields?: Record<string, unknown>): void;
}

export function createLogger(minLevel: Level = 'info'): Logger {
  const emit = (level: Level, msg: string, fields?: Record<string, unknown>): void => {
    if (ORDER[level] < ORDER[minLevel]) return;
    const line = JSON.stringify({ level, msg, ts: Date.now(), ...redact(fields ?? {}) });
    (level === 'error' ? console.error : console.log)(line);
  };
  return {
    debug: (m, f) => emit('debug', m, f),
    info: (m, f) => emit('info', m, f),
    warn: (m, f) => emit('warn', m, f),
    error: (m, f) => emit('error', m, f),
  };
}

/** 血缘:每条 AI 产物带来源 + 产出它的实现/版本号,多实现可并存可审计。 */
export function logProvenance(
  logger: Logger,
  p: { source: string; impl: string; version: string; count: number },
): void {
  // 只记码值/计数/实现名;载荷(答案/原文/向量值)绝不在这里出现
  logger.info('provenance', p);
}
```

纪律:

- **库代码只取 logger 发事件**,不在库里配日志后端;后端配置(等级、是否 pino)在 app 入口装一次。
- **隐私不落盘**:payload(答案、原文、向量值、用户输入、prompt)绝不直接 log。结构化 logger 的红化键集是兜底,但纪律是**主动不传**——只记码值 / 计数 / 耗时 / 枚举码。把这条写进 `kernel` 的 CLAUDE.md 当硬纪律。
- **secret 不落盘**:见 §5。`SENSITIVE` 集覆盖常见 key,但同样以"主动不传"为先。
- **血缘进、隐私出** —— 与 §10 的"约束下沉"配套。

> 进阶可选:Node 端要高性能结构化日志时引 `pino`;浏览器端这套 `console` + JSON 已够。

---

## 7. 提示词:随 kernel 出厂 + 严格渲染

提示词 `.md` 放 `packages/kernel/src/prompts/<domain>/*.md`,随 kernel 包出厂(改提示词 = 改仓库 + 重新构建,更规范;运行时热换是另一层功能,不在此)。加载方式按运行环境分两路,但**严格渲染**这条统一:模板里出现但未提供的 `{{var}}`,**直接抛错**而非静默替成空串——对应 Python Jinja2 的 `StrictUndefined`。

```ts
// packages/kernel/src/prompts.ts
function strictRender(template: string, vars: Record<string, string>): string {
  return template.replace(/\{\{\s*(\w+)\s*\}\}/g, (_, key: string) => {
    const value = vars[key]; // noUncheckedIndexedAccess 下类型是 string | undefined
    if (value === undefined) {
      throw new Error(`missing prompt variable: {{${key}}}`); // 不静默失败,且无需 ! / as
    }
    return value; // 收窄后这里就是 string
  });
}

// Node / vitest / CLI:用 fs + import.meta.url 定位(不依赖 CWD)
import { readFileSync } from 'node:fs';
export function renderPromptNode(name: string, vars: Record<string, string>): string {
  const url = new URL(`./prompts/${name}.md`, import.meta.url);
  return strictRender(readFileSync(url, 'utf8'), vars);
}

// Bundler(Vite / Next):用 ?raw import 把 .md 内联进 bundle
// import answerTpl from './prompts/rag/answer.md?raw';
// export const renderAnswer = (vars: Record<string, string>) => strictRender(answerTpl, vars);
```

两路并存的原因:vitest / CLI 在真实文件系统上跑,用 `fs.readFileSync(new URL(..., import.meta.url))` 按模块位置定位、不依赖 CWD;浏览器 bundle 里没有文件系统,用 bundler 的 `?raw`(Vite 原生、Next 经 loader)把 `.md` 内容编译期内联。两者都让"提示词随代码版本走",dev / prod 一致。

> 进阶可选:需要循环/条件等模板逻辑时引 Handlebars / Eta;默认这套占位符替换 + 缺变量报错已覆盖多数提示词场景。

---

## 8. 结构:pnpm + Turborepo monorepo,package-per-domain

深度来自 **monorepo**(多包),不是一个包里堆深文件夹。pnpm workspace 包 ≈ Cargo crate / SPM target:包级依赖隔离 + 可解析的依赖图。"修 reranker"应定位到 `packages/retrieval/...`,无需搜索。

```
repo/
├── package.json              # 根:private、packageManager=pnpm、scripts(turbo run …)
├── pnpm-workspace.yaml       # packages: ["packages/*", "apps/*"]
├── turbo.json                # pipeline:typecheck / lint / test / build(dependsOn 拓扑)
├── tsconfig.base.json        # 严格基线(§2.1),被所有包 extends
├── eslint.config.mjs         # flat、类型感知、共享
├── .prettierrc.json  .prettierignore  .gitignore  .env.example
├── ci.sh  Makefile  README.md  CLAUDE.md   # 根路由表
├── docs/adr/
├── configs/settings.json     # 环境相关结构化配置(非 secret)
├── packages/
│   ├── kernel/               # 跨切面:config(Zod env)/ logging / prompts。零 UI 框架、零 SDK
│   │   ├── package.json  tsconfig.json  CLAUDE.md
│   │   └── src/{config.ts, logging.ts, prompts.ts, prompts/rag/answer.md, index.ts}
│   ├── domain/               # ports(interface)+ models(Zod schema)+ errors。零 SDK、零 UI 框架
│   │   ├── package.json  tsconfig.json  CLAUDE.md
│   │   └── src/{ports.ts, models.ts, errors.ts, index.ts}
│   ├── adapters/             # 实现;唯一可碰 SDK;MockProvider 默认。依赖 domain + kernel
│   │   ├── package.json  tsconfig.json  CLAUDE.md
│   │   └── src/{mock.ts, factory.ts, index.ts}
│   ├── retrieval/  generation/   # 示例领域包(由 scaffold 生成,不内置)
└── apps/
    ├── web-vite/             # React + Vite 薄壳(composition root)。依赖 domain/kernel/adapters/领域包
    │   ├── package.json  tsconfig.json  vite.config.ts  index.html  CLAUDE.md
    │   └── src/{main.tsx, App.tsx}
    └── web-next/             # Next.js App Router 薄壳(composition root)
        ├── package.json  tsconfig.json  next.config.ts  next-env.d.ts  CLAUDE.md
        └── app/{layout.tsx, page.tsx}
```

要点:

- **依赖方向**:`domain`(零 SDK、零框架)← 领域包(`retrieval`/`generation`,依赖 `domain` + `kernel`)、`adapters`(依赖 `domain` + `kernel`,+ SDK 懒加载);`kernel` 零框架零 SDK;`apps/*` 依赖全部(composition root,唯一碰 React/Next)。包名 `@__SCOPE__/kernel` 等,模块名(kernel/domain/adapters/<domain>)与 scope 无关。
- **框架无关核心**:`kernel`/`domain`/`adapters`/领域包**全部零 React/Next**——核心逻辑可在 Vite、Next、甚至纯 CLI 下复用,框架只是边缘的壳。`check_conformance` 机械检查 `domain` 的零框架(react/react-dom/next/vue/svelte/@angular/core 黑名单),其余核心按约定零框架。这条让"换壳""加一个 RN/Electron 壳"成本极低。
- **pnpm `packages/*` glob 自动纳入**:新建一个 `packages/<x>/` 目录带 `package.json`,pnpm 立即把它视为 workspace 成员——像 Cargo,无需改 `pnpm-workspace.yaml`。这是 scaffold 加领域包零接线的基础。
- **workspace 内引用用 `workspace:*`**:`"@scope/domain": "workspace:*"`,pnpm 软链到本地包,改了即时生效。

### 8.1 每个包一个 CLAUDE.md(分层上下文)

把"分层上下文"落到目录:根 `CLAUDE.md` 是**路由表**(只放硬约束 + 去哪找),每个包目录的 `CLAUDE.md` 写本包的职责、依赖方向、本地契约(`domain` 的"零 SDK、零框架"、`adapters` 的"错误归一"、`kernel` 的"载荷不落盘")。`check_conformance.py` 要求根 + 每个 `packages/*`、`apps/*` 都有。好处:agent 进到某包工作时,就近拿到的是这一层的精确约束,而非读一份大文档被噪声稀释。

### 8.2 可导航性

命名即路径,是导航层面的"类型即接口契约";monorepo 把它提到包级。按能力分(不按 `components/`/`utils/` 平铺),一直拆到叶子文件只剩单一职责。深结构 + 一致命名,让"哪段代码在哪"无需搜索。"修 reranker"→ `packages/retrieval/src/reranking/`。

---

## 9. 模型无关:provider 接口缝 + 零-SDK 零框架的 domain

模型是可热插拔的商品。一旦正确性依赖某个具体模型的输出,你就和它联姻——把正确性、可测性、可审计性从模型里抽出来,钉在接口与确定性代码上。

### 9.1 接口在 domain,零 SDK 零框架

每个外部依赖 = `packages/domain` 里一个最小接口。领域逻辑只依赖接口,**import 厂商 SDK 数为 0、import UI 框架数为 0**(`check_conformance.py` 解析 `package.json` 强制)。

```ts
// packages/domain/src/ports.ts —— 零 SDK、零框架
export interface LLM {
  complete(prompt: string): Promise<string>;
}

export interface Embedder {
  embed(texts: string[]): Promise<number[][]>;
}

// packages/domain/src/errors.ts —— 边界错误归一的目标类型
export class ProviderError extends Error {
  constructor(
    message: string,
    readonly code: 'unavailable' | 'rate_limited' | 'decoding' = 'unavailable',
  ) {
    super(message);
    this.name = 'ProviderError';
  }
}
```

### 9.2 MockProvider 作默认(不是测试桩)

```ts
// packages/adapters/src/mock.ts —— 确定性、离线、无需 key、零 SDK
import type { LLM, Embedder } from '@__SCOPE__/domain';

export class MockLLM implements LLM {
  complete(prompt: string): Promise<string> {
    return Promise.resolve(`mock-answer(${prompt.length})`); // 确定性:同输入同输出
  }
}

export class MockEmbedder implements Embedder {
  embed(texts: string[]): Promise<number[][]> {
    return Promise.resolve(texts.map((t) => [t.length, 0, 0])); // 确定性、数量保持
  }
}
```

MockProvider 是**默认实现**:app、测试、CI 默认走 Mock,跑得快、稳、免费、不被随机性污染、不联网。"无 key 也能 demo/test 跑绿"设成硬验收(smoke 测试)。

### 9.3 真实 SDK:optional dep + 动态 import 懒加载

真实后端如 OpenAI 用 `optionalDependencies`/`peerDependencies`(默认不强装),且**只在 `adapters` 里、用动态 `await import()` 懒加载**——这样默认 build/test 完全离线、不拉 SDK,只有真用到时才加载:

```ts
// packages/adapters/src/openai.ts —— 真实后端写法示意
import type { LLM } from '@__SCOPE__/domain';
import { ProviderError } from '@__SCOPE__/domain';

export class OpenAIProvider implements LLM {
  constructor(private readonly apiKey: string) {}

  async complete(prompt: string): Promise<string> {
    // 动态 import:openai 是 optionalDependency,只在这条路径被真正加载
    const { default: OpenAI } = await import('openai');
    const client = new OpenAI({ apiKey: this.apiKey });
    try {
      const res = await client.chat.completions.create({
        model: 'gpt-4o',
        messages: [{ role: 'user', content: prompt }],
      });
      return res.choices[0]?.message.content ?? ''; // noUncheckedIndexedAccess 逼你处理 [0] 可能 undefined
    } catch (err) {
      // 边界归一:网络/超时/API 错 → ProviderError;程序 bug 不在此 catch,照常上抛
      throw new ProviderError(err instanceof Error ? err.message : 'openai failed', 'unavailable');
    }
  }
}
```

### 9.4 装配缝

`adapters/factory.ts` 按 config 选实现并注入,或在 app 壳里组装(composition root)。业务代码不写裸厂商名,只调 `makeLLM(config)`:

```ts
// packages/adapters/src/factory.ts
import type { LLM } from '@__SCOPE__/domain';
import { MockLLM } from './mock.js';

export async function makeLLM(config: { provider: 'mock' | 'openai'; apiKey?: string }): Promise<LLM> {
  switch (config.provider) {
    case 'mock':
      return new MockLLM();
    case 'openai': {
      if (!config.apiKey) throw new ProviderError('openai requires apiKey');
      const { OpenAIProvider } = await import('./openai.js'); // 懒加载,Mock 路径不碰
      return new OpenAIProvider(config.apiKey);
    }
    default: {
      const _exhaustive: never = config.provider; // §4.2 穷尽
      throw new Error(`unknown provider: ${String(_exhaustive)}`);
    }
  }
}
```

### 9.5 一致性契约(conformance kit)

任何号称实现了某接口的类(Mock 与真实后端)都跑同一组行为不变量——可插拔只在所有实现行为一致时才安全,否则 bug 以"换了模型后偶发"出现:

```ts
// packages/adapters/src/conformance.ts —— 共享契约,Mock 与真实后端复用
import { expect } from 'vitest';
import type { Embedder } from '@__SCOPE__/domain';

export async function assertEmbedderContract(embedder: Embedder): Promise<void> {
  const texts = ['a', 'b'];
  const first = await embedder.embed(texts);
  const second = await embedder.embed(texts);
  expect(first).toEqual(second);          // 确定性
  expect(first).toHaveLength(texts.length); // 数量保持
}

// mock.test.ts
import { test } from 'vitest';
test('mock embedder obeys contract', async () => {
  await assertEmbedderContract(new MockEmbedder());
});
// 真实后端在有 key / 启用真实 provider 时加一个 test 复用同一函数。
```

> **`interface` vs 闭包结构 的取舍**:多数场景用 `interface` + `class implements`(可读、可 `instanceof`、IDE 友好),这是 Swift `protocol` 的对应。若实现是无状态的一组函数、或想避免 class,用**对象字面量 + `satisfies`**(`const mockLLM = { complete: async (p) => … } satisfies LLM`)或返回闭包的工厂函数同样满足接口——TS 是结构化类型,只要形状匹配即可。本标准只规定"缝在 `domain`、默认 Mock、零 SDK 零框架"这一架构约束,内部用 class 还是闭包按可读性定。

---

## 10. 让 AI 输出可信:把约束下沉到控制流,而非写进 Prompt

Prompt 是软约束,温度 / 越狱 / 长上下文都能绕过;只有沉到代码的约束,才能从"概率性遵守"变成"结构上不可能违反"。本节偏原则(不像结构那样能完全机械检验),但对 AI-touching 代码是上位纪律。

- **Constrain, don't ask**:对不可妥协属性(不编造、必引用、不越权),让模型物理上无法违反——命中事实时答案由代码从结构化值确定性合成、模型散文整段丢弃;无事实时编排层改写成"查不到"。迁移:列"绝不能发生"清单,逐条问"模型能否在听话的同时仍违反它",凡"能"的就移出模型。
- **收窄发射面**:不让模型自由生成关键载荷——让它从一个 **TS 联合字面量** 或 **Zod `enum`** 里选、或调返回三态(`found`/`not_found`/`unrecognized`)的工具,最终值取自工具结果而非模型文本。TS 的**可辨识联合 + 穷尽 `switch`**(§4.2)天然是受控发射面,且编译器保证你处理了每个 case;Zod `enum` 在边界把模型输出 parse 成这个联合,非法即归一成已知态(见 §3 的 `safeParse` 示例)。模型能犯的错与它能输出的"面积"成正比。
- **安全门确定性、独立、永不可插拔**:理解类(意图解析)可替换;安全决策(越权 / 敏感隔离)做成确定性代码,从原始输入独立重判,不信任可插拔组件的输出。可替换的是智能,不是护栏。
- **血缘进、隐私出**:见 §6(`logProvenance` + 红化纪律)。每条产出带来源 + 实现 / 版本号,trace 只记码值 / 计数 / 耗时,绝不落答案 / 数值 / 原文。

---

## 11. 把人类的隐性兜底外化成会失败的工件

人靠经验、记忆、羞耻感判断"做完没""文档过时没";agent 没有这些,只优化能观测到的反馈。每加一个会失败的检查,就把一份隐性知识变成 agent 无法悄悄绕过的硬约束。

- **加宽的零警告门**(§1):一条 `set -euo pipefail` 脚本串起 tsc `--noEmit` + eslint `--max-warnings 0`(类型感知)+ prettier `--check` + vitest(smoke + conformance)+ build(两壳);任一项非零即没完成。人和 agent 共用同一条判据,用 pre-push hook 钉死。
- **漂移守卫 + 结构不变量**:`check_conformance.py` 解析 `package.json`(纯 JSON)与 `tsconfig`(`npx tsc --showConfig`),机械检查 `domain` 零-SDK-零框架、严 flags 在位、逃生舱禁令在 eslint、ci.sh 串齐五步、每包有 CLAUDE.md。描述代码的 markdown 可带 `covers:` 元数据,被覆盖路径失效即红——给"上下文骗了 agent"装真实性保险丝。
- **自描述工件从真实代码派生**:依赖 / 拓扑图从 pnpm 的 workspace 图(`pnpm list --depth -1` / `pnpm-workspace.yaml`)与 `turbo.json` 的 pipeline 派生,而非手画;手维护的图必然腐烂,腐烂的图比没有更危险——会自信地误导后续 agent。Turbo 的 `dependsOn` 本身就是机器可读的真实依赖声明。
- **分层上下文**(§8.1):根路由表 + 每包就近契约,而非一份大文档读到底。上下文窗口稀缺,"什么都塞"稀释信号。

---

## 12. 驾驭 AI 做大工作:可拆分、可逐步验证、可对抗审查

把 AI 当可监督的劳力,而非无监督自动驾驶。这是工作流层(可作另一个姊妹技能),轻量版规则:

- **先决策再编码(ADR,`docs/adr/`)**:架构 / 产品决策写成编号、不可变的 ADR(背景 + 选定 + 被否决备选及理由)。AI 最擅长明确约束下填实现,最不可靠的是替你做含糊取舍;否决理由还防它重走已排除的路。
- **TDD 红灯先行,测试即不可动摇的规格**:每个改动先写会失败的 Vitest 测试,再实现到绿,**绝不**为通过而弱化测试;给 subagent 的任务直接附失败测试当验收。
- **拆成编号步骤、每步独立绿灯**:大重构拆有序步骤,每步一次提交、跑完整门禁再进入下一步,绝不攒巨型 diff——把失败爆炸半径压到一步之内。
- **分解→并行→综合**:主 agent 拆边界清晰、规格完整的子任务并行分派,逐个审 diff 并在提交前过门。monorepo 的包边界天然是并行单元。
- **对抗式独立复审**:写完后另起独立、带敌意的多视角复审("假设它有错,去证伪"),优先审测试盖不到的产物(图、文档、取舍)——同一 agent 既写又夸会系统性确认偏差。

---

## 附:Python / Swift / Rust 姊妹标准的映射速查

| 关注点 | Python 标准 | Swift 标准 | Rust 标准 | **前端标准** |
|---|---|---|---|---|
| 静态类型 | mypy `--strict` | 编译器(免费) | 编译器(免费) | **TypeScript `strict` + 更严 flags(`tsc --noEmit`)** |
| 运行时类型 | beartype + claw hook | 不需要(编译期、无擦除) | 不需要 | **需要(TS 运行时擦除)!但无 import-hook → Zod 只在边界 parse** |
| "无逃生舱" | 禁裸 `Any` | 关死 `!`/`try!`/`as!`/`@unchecked Sendable` | `#![forbid(unsafe_code)]` | **禁 `any`(+ `no-unsafe-*`)、禁 `!`、`@ts-ignore`→`@ts-expect-error` 带说明、危险 `as` 靠 `no-unsafe-*` 抓** |
| 逃生须记录 | `# type: ignore[code] # 原因` | `// swiftlint:disable:next … — 原因` | `#[allow(clippy::…)] // 原因` | **`// eslint-disable-next-line <rule> -- 原因` 或 `@ts-expect-error -- 原因`** |
| 不静默失败 | 无裸 except、StrictUndefined | `throws` + typed `throws(E)` | `Result`/`thiserror` | **不吞 catch、穷尽 switch(`never`)、`no-floating-promises`、error boundary、边界归一 `ProviderError`** |
| 边界校验 | pydantic | `Codable` + newtype | `serde` + newtype | **Zod(`z.infer` + `safeParse`,parse don't validate)** |
| 结构 | src 布局 + domain-first 深目录 | SPM target-per-domain | Cargo workspace + crate-per-domain | **pnpm + Turborepo monorepo + package-per-domain** |
| 模型无关 | `ports/`+`adapters/`,核心零 SDK | `Domain`(protocol)+`Adapters`,零 SDK | `domain`(trait)+`adapters`,零 SDK | **`domain`(interface)+`adapters`,domain **零 SDK 且零 UI 框架**** |
| 可选后端 | optional extras + lazy import | package traits + `.when(traits:)` | `optional` 依赖 + feature 门控 | **`optionalDependencies` + 动态 `await import()` 懒加载(仅 adapters)** |
| 装配缝 | `ports/factory.py` | `App` 组装根按 config 选 | `app` 组装根 `match` | **`adapters/factory.ts` 按 config 选 / app 壳 composition root** |
| 配置 | pydantic-settings + yaml | Codable `AppConfig` + 分层 | figment + toml | **Zod 校验的 env(t3-env 模式)+ 默认 < `settings.json` < env** |
| 日志/血缘/隐私 | logging + log_provenance + SENSITIVE | `os.Logger` + privacy 插值 | tracing + log_provenance | **结构化 JSON logger + 红化 + `logProvenance`(浏览器/Node 双端;pino 进阶可选)** |
| 提示词 | PackageLoader(随 wheel) | `Bundle.module`(SPM resources) | `include_str!`(编译期嵌入) | **随 kernel 出厂:Node `fs`+`import.meta.url` / bundler `?raw` + 严格渲染(缺变量抛错)** |
| 门禁 | ruff+mypy+drift+pytest | swift-format+swiftlint+build+test | fmt+clippy -D+doc+test+cargo-deny | **tsc `--noEmit` + eslint `--max-warnings 0` + prettier `--check` + vitest + build(turbo 编排)** |
| 分层上下文 | 根 CLAUDE.md + 就近契约 | 根 + 每 target CLAUDE.md | 根 + 每 crate CLAUDE.md | **根 CLAUDE.md + 每 package/app CLAUDE.md** |
| 脚手架/合规 | scaffold.py / check_conformance.py | scaffold.py / check_conformance.py(`dump-package`) | scaffold.py / check_conformance.py | **scaffold.py / check_conformance.py(解析 package.json;tsconfig 用 `tsc --showConfig`)** |
