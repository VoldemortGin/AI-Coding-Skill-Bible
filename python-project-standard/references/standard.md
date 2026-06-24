# Python AI 编码规范

> **目标**:用机器可读的类型契约 + 测试,给 AI agent 一个能自主收敛的反馈闭环,最大化自动化编码的效率与可靠性。
>
> 适用对象:人类开发者 **和** AI 编码 agent(可直接作为 `CLAUDE.md` / `AGENTS.md` 的一部分)。
>
> **技术基线(只用当前主流大版本,不背历史包袱):** Python **3.13** · mypy `--strict` · ruff · beartype · pydantic v2 + pydantic-settings · Jinja2 · Hypothesis。
> 一律现代写法:**不写** `from __future__ import annotations`(它把全部注解字符串化、与 beartype 运行时解析冲突——前向/自引用类型按需加引号即可);**不用** `typing.List/Dict/Optional`;优先 PEP 695 的 `type` 别名与 `class Box[T]` 泛型语法。

---

## 0. 核心原则

AI agent 自主编码的瓶颈是**反馈信号的质量**。动态 Python 信号太弱:代码能跑通却悄悄做错事,agent 无法判断对错、无法自我纠正。本规范的全部目的就是补强这个信号:

- **mypy(静态)** —— 不运行就覆盖所有分支,给出编译期错误。
- **beartype(运行时)** —— 在实际执行路径上验证连静态层面都看不见的真实值(LLM 输出、反序列化数据)。
- **测试** —— 验证类型管不了的**行为**。

三者合一,把"可能不对"变成**精确到参数、可被 agent 直接解析并修复**的错误。类型越完整,agent 的错误假设越少、修复循环收敛越快。

> ⚠️ 类型约束的是**形状(shape)**,不是**行为(behavior)**。类型全对、逻辑写错的函数依然存在。类型是底座,测试管行为,缺一不可。

---

## 1. 反馈闭环:一条命令的质量门

整个自动化的核心原语是**一条命令**,把所有检查串起来、输出机器可读结果。agent 每改一次代码就跑一次,解析错误,修复,重复,直到全绿——这一步不需要人介入。

按"快→慢"排,让 agent 尽早拿到反馈:

1. `ruff format --check` —— 格式
2. `ruff check` —— lint(含强制类型注解的 `ANN` 规则)
3. `mypy` —— 静态类型(全分支)
4. `pytest`(beartype 激活)—— 运行时类型 + 行为

具体命令见[附录](#附录配置与样板)。**禁止**让 agent 用零散的、需人工判读的检查方式;必须收敛到这一条命令。它是 agent 唯一的正确性判据,不允许"看起来没问题就提交"。

---

## 2. 静态类型 — mypy `--strict`

- 每个函数的**参数和返回值**都必须有类型注解,不留空(`--strict` 强制)。
- **禁止裸 `Any`**。需要动态时用 `object`、`Protocol`、`TypeVar`、`Union`、`Literal` 收窄。
- 泛型必须参数化:`list[str]` 而非裸 `list`,`dict[str, int]` 而非裸 `dict`。
- 类型别名用 PEP 695 的 `type` 语句:`type UserId = int`(不用 `TypeAlias`)。
- `# type: ignore` 必须带**错误码和理由**(`# type: ignore[arg-type]  # 原因…`),视为待还的技术债;`--strict` 下失效的 ignore 会直接报错,升级依赖时记得清理。
- `__init__.py` 的转发要显式(`from .x import y as y` 或 `__all__`),否则 `no-implicit-reexport` 下别人 import 不到。

新代码从严无例外。若并入存量代码,用 `[[tool.mypy.overrides]]` 按模块临时降级。

---

## 3. 运行时类型 — beartype

**机制:中心化布尔开关(pydantic-settings)+ `beartype.claw` import hook。** 不手动写 `@beartype` 装饰器,**绝不靠注释/反注释源码**来开关——那是不可自动化的体力活,污染 git diff,回归调试还得逐个改回。

开关由 `core/settings.py` 里的 `Settings` 暴露(`beartype_on`,默认跟随 `is_debug`),由包的 `__init__.py` 读取并条件安装 claw hook。代码见[附录](#附录配置与样板)。

### ❗ 关键约束:import 顺序(最容易踩的坑)

claw hook 只 instrument 它**安装之后**才被 import 的模块,已 import 的不会被追溯处理。由此三条铁律:

1. **hook 必须在 `__init__.py` 最顶部安装**,后续导入的子模块才会被检查。
2. **hook 之前的 import 面要最小**:在它之前只能导入 `settings`。因此 `core/settings.py` 必须是**叶子模块**——只依赖标准库 + 第三方配置库(pydantic-settings、PyYAML),**不 import 任何想被检查的一方代码**。第三方依赖不受此约束。
3. **`core/__init__.py` 必须保持空**:导入 settings 会先经过它,若在此 re-export `paths`/`logging`/`prompts`,这些会在 hook 之前被导入、从而漏检。

> **为什么放 `__init__.py` 就够,不用在每个入口重复装 hook:** 任何对 `myproj` 的导入都会**先**执行 `myproj/__init__.py`,所以它是所有调用路径上唯一、保证最先跑的钩子点——cli、scripts、tests、别的包导入它,都自动覆盖。**前提是"从包进入"**:用 `import myproj.X` / `python -m myproj.cli` / console_script / `uv run`。**别直接跑散文件**(`python src/myproj/cli.py`)——那样不会触发包的 `__init__.py`(hook 不装),相对导入也会坏。另外 hook 进程内只装一次:pre-hook 加载过的模块会被 `sys.modules` 缓存、整个进程不再被检查,所以 pre-hook 面要严格只有 settings。

### 三档策略(利用"开发测试可以慢"这个容忍度)

| 环境 | beartype 策略 | 由谁控制 | 理由 |
|---|---|---|---|
| 本地开发 | `O1`(常数,抽样) | 默认 | 快反馈,不拖慢迭代 |
| CI / 测试 | `On`(线性,全量) | 检测到 `CI` 环境变量 | 慢无所谓,要抓干净——agent 的质量门 |
| 生产 | 关闭 | `APP_BEARTYPE_ON=false` | 零开销;边界安全交给 pydantic(§4) |

> beartype **默认开启**(`beartype_on=True`),覆盖本地开发与测试;**仅生产**用 `APP_BEARTYPE_ON=false` 关闭。`On`/`O1` 只决定开启后的检查强度(`CI` 环境变量选 `On`)。`O1` 默认抽样,单次调用可能漏掉容器里没抽到的坏元素,所以确定性最重要的 CI 必须用 `On`。

---

## 4. 边界 — pydantic

**所有穿过进程边界的数据,都必须在入口处建模并校验**,不要信任它符合声明的类型:LLM 结构化输出、工具调用返回、HTTP 载荷、配置文件、用户输入、任何反序列化结果。

```python
from pydantic import BaseModel

class LLMToolCall(BaseModel):
    name: str
    arguments: dict[str, object]

call = LLMToolCall.model_validate(raw_json_from_llm)  # 在边界 parse,而非信任
```

**beartype vs pydantic 决策规则:**

- **穿过进程边界的数据 → pydantic**:需要校验合法性,常常还要转换/收窄(字符串转 datetime、约束值范围)。
- **进程内部的契约 → beartype**:数据已在掌控内,只想运行时断言"形状没跑偏"作为保险,不需转换。

RAG/agent 流水线里,LLM 输出和工具结果在 pydantic 边界一卡,正好抓住 mypy 看不见、最容易出 bug 的那一类(模型返回结构跑歪)。

---

## 5. 测试 — 让运行时检查真正生效

beartype **只能检查实际执行到的路径**,所以它的有效性 = 测试覆盖。

- **边界优先**:对所有 pydantic 边界,用真实样本 + **对抗样本**(缺字段、类型错、空值、超长)测试。
- **Hypothesis(property-based testing)是放大器**:自动生成大量输入 → 把各种路径都跑一遍 → beartype 在每次调用上验证类型 → 自动发现人工想不到的违例。这套组合直接实现 agent "自己发现 bug"。
- 覆盖率不是目标本身,但**没跑到的分支 beartype 管不着**,核心路径的覆盖要保证。

---

## 6. 代码形态 — 为 AI 可读性服务

类型是 agent 读代码时的接口契约;形态越清晰,agent 假设越少、改得越准。

**现代写法(3.13)**

- 泛型用 PEP 695:`def first[T](xs: list[T]) -> T:`、`class Box[T]: ...`,不再手写 `TypeVar`。
- 类型别名:`type Json = dict[str, "Json"] | list["Json"] | str | int | float | bool | None`。
- 枚举用 `StrEnum`(`from enum import StrEnum`)。
- 覆写方法标 `@override`(`from typing import override`),让签名漂移在静态层暴露。

**通用约束**

- **小而专的函数**:既是 beartype/pydantic 的天然边界,也让 agent 容易推理。
- **类型即契约**:签名要能让人/agent 不读函数体就理解接口;配简短 docstring 说明契约。
- **避免 `Any` 和 `# type: ignore`**:每一个都是 mypy、beartype、agent 三方共同的盲区。
- **不要静默失败**:让错误响亮且定位明确。beartype 的违例信息、Jinja2 的 `StrictUndefined` 都是这种"宁可报错"的取向。不要用裸 `except` 吞掉。

---

## 7. 项目结构

布局参考 lightning-hydra-template,但**去掉 Hydra**(理由见 §7.4),配置走 pydantic-settings。

### 7.1 src 布局 + 真实包名,不需要 rootutils

- **永远用 src 布局**(`src/<name>/`):PyPA 推荐,强制"装了才能测",能抓打包 bug。
- **一开始就给包起真名,自用也别叫 `import src`。** 自用 vs 上 PyPI 的唯一区别只是这个名字取项目名还是发行名;布局和导入路径都不变,以后抽库/上架零改动。
- **不需要 `.project-root` / `rootutils`。** 那是 lightning-hydra-template 把 `src` 当包、且不安装就 `python src/train.py` 的产物,所以要改 `sys.path`。我们**把包装上**(editable),装完 `import myproj` 在任何 CWD 都能用,`pytest`、`scripts/` 里的脚本也都能 import 到。给可安装的包用 rootutils 改路径是反模式。
- **找文件**与 import 无关:包内自带资源用 `importlib.resources` / `PackageLoader`;根级内容(configs/data)走 settings + 环境变量;若想要 dev 下 CWD 无关的根锚点,用一个 8 行的"向上找 `pyproject.toml`"即可(见附录 `settings.py` 的 `_find_project_root`),无需 rootutils 也无需自定义标记文件。部署时一律以环境变量显式指定路径。

**开发期怎么跑(editable 安装是一次性的)**

editable 安装不拷贝代码,而是让 `import myproj` 直接指向你的 `src/myproj/` 源码。**装一次之后,改 src/ 里的代码下次运行立刻生效,不用重装**;提示词同理(`PackageLoader` 在 editable 下也指向真实源码目录,dev 关缓存即时生效)。

用 uv,日常根本不用手动"安装":

```bash
uv sync                       # 一次性:建环境 + editable 安装本项目
uv run python -m myproj.cli   # 直接跑实时源码
uv run pytest                 # 跑测试,同样实时
```

**只有改了依赖(`uv add` 某个库)才需要重新同步;改自己的代码永远不用。**

### 7.2 可复用代码全进 src/

- 任何可复用的**领域逻辑**都放 `src/<pkg>/`,**哪怕只被 `scripts/` 或 `tests/` 调用**。
- 这和 beartype 协同:claw 只 instrument 包本身,`scripts/`、`tests/` 在包外不被自动检查;逻辑进 src/ 才会被运行时类型检查覆盖,留在脚本里就是盲区。
- **唯一例外**:测试专属脚手架(fixtures、mock 工厂、`conftest.py`)留在 `tests/`。判据:可复用领域逻辑 → src/;只为测试存在的基础设施 → tests/。

### 7.3 文件放哪:一条原则

- **随代码出厂、只读、每个部署都一样 → 包内**:`prompts/`(§7.5),用 `PackageLoader` / `importlib.resources` 定位,自动进 wheel,dev/prod 一致。
- **环境相关、可覆盖、可能含密钥 → 根级 + env**:`configs/settings.yaml`(§7.4),不进 wheel。
- **运行期可写 → 根级 + settings**:`data/`、`logs/`,路径来自 settings(可被 `APP_*_DIR` 覆盖)。

### 7.4 core/:跨切面基础设施的唯一来源

通用东西一处定义、处处调用,避免重复甚至出错。放 `core/`:

- **`settings.py`** —— pydantic-settings `Settings`,环境变量 + `.env` + `configs/*.yaml` 的统一入口。**必须是 beartype 叶子**(§3)。
- **`paths.py`** —— 类型化路径:包内自带资源用 `importlib.resources`;运行期可写目录从 settings 取。
- **`logging.py`** —— 定义 `setup_logging()`(唯一来源)。**库代码只 `logging.getLogger(__name__)`**,绝不在别处配置日志;`setup_logging()` 由入口启动时调用一次,幂等。
- **`prompts.py`** —— 提示词加载轮子(§7.5)。
- **`core/__init__.py` 保持空**(§3 铁律 3)。

### 7.5 配置:configs/ 经 pydantic-settings 并入 Settings(替代 Hydra)

复杂的全局配置外置成 `configs/settings.yaml`,由 `core/settings.py` 通过 **`YamlConfigSettingsSource`** 并入同一个 `Settings` 对象——**这就是 Hydra 配置文件的类型化替代**:你拿到文件式结构化配置,却不引入 Hydra `DictConfig` 那个 `Any` 黑洞。

- 复杂全局变量用**嵌套 pydantic 模型**表达(如 `retriever: RetrieverConfig`),在 yaml 里写嵌套结构。
- 优先级从高到低:**构造参数 > 环境变量 > `.env` > yaml > secrets**。即 yaml 当结构化基线,环境变量按部署覆盖;`APP_RETRIEVER__TOP_K` 可逐项覆盖嵌套字段。
- configs/ 是**环境相关的配置值**,不进 wheel(部署各异、可能含密钥),与"随代码出厂"的 prompts 正相反。

> 若日后需要重度实验扫参,再考虑 `tyro`/`jsonargparse` 或仅在实验层引入 Hydra;app/密钥始终走 pydantic-settings。

### 7.6 prompts/:包内提示词 + 统一加载轮子

- 提示词放**包内** `src/<pkg>/prompts/`(`prompts/<name>.md`,可带子目录),由 `core/prompts.py` 用 **`jinja2.PackageLoader`** 加载,其他代码 `from myproj.core.prompts import render_prompt` 调用。
- **一劳永逸**:`PackageLoader` 按包名定位,不依赖 CWD/项目根;包内 `.md` 用 hatchling 会**自动**打进 wheel(无需配 package_data);dev(editable)与生产(wheel)行为完全一致,没有"以后打包再搬"的分支。
- 用 Jinja2 + **`StrictUndefined`**:缺模板变量**直接报错**而非静默空串,契合"不静默失败"。dev 下关缓存,改了即时生效。
- 取舍:提示词从此**随代码版本走**,改提示词 = 改仓库 + 重新部署(更规范);要运行时热换提示词是另一层功能(外部提示词存储),不在此。

### 7.7 目录树

```
repo/
├── configs/
│   └── settings.yaml        # 环境相关配置值;不进 wheel(由 settings 的 YAML 源读取)
├── data/  logs/             # 运行期可写产物,gitignore
├── notebooks/
├── scripts/                 # 薄:只编排,逻辑全在 src/
├── src/
│   └── myproj/              # ← 真实包名(自用也别叫 src);上架就是发行名
│       ├── __init__.py      # 唯一安装 beartype claw hook 的地方
│       ├── prompts/         # 提示词随包出厂(PackageLoader 加载,dev/prod 一致)
│       │   └── rag/
│       │       └── answer.md
│       ├── core/
│       │   ├── __init__.py   #   必须为空(否则 paths/logging/prompts 会在 hook 前被导入)
│       │   ├── settings.py   #   Settings(env + .env + configs/*.yaml)—— 叶子模块
│       │   ├── paths.py      #   类型化 Paths:包内资源 vs 运行期可写目录分开
│       │   ├── logging.py    #   定义 setup_logging();库代码只 getLogger
│       │   └── prompts.py    #   提示词加载轮子:render_prompt / get_prompt
│       ├── <domain>/        # 业务模块:retriever / chunker / agent ...
│       ├── cli.py           # 入口:启动时调 setup_logging() 一次、读 settings
│       └── ...
├── tests/
│   ├── conftest.py          # 测试专属 fixtures —— 留这里,不进 src/
│   └── ...
├── .env.example
├── .pre-commit-config.yaml
├── pyproject.toml
└── README.md
```

### 7.8 调用约定:scripts / notebooks / tests 里用 src/

三者都在包外,而 `myproj` 是 editable 安装的,所以**统一像用第三方库一样** `from myproj.X import Y`——零 sys.path 操作、零 rootutils。导入 `myproj.*` 会自动触发 §3 的 hook,你调用的 src/ 代码因此被运行时检查(策略按环境);它们**自身**的代码在包外、不被 instrument(可复用逻辑本就该在 src/,见 §7.2)。

前置:`uv sync` 一次(editable 安装),之后改 src/ 即时生效。

**tests/**

```bash
uv run pytest            # 本地:beartype O1
CI=1 uv run pytest       # CI:beartype On 全量
```

- `from myproj.pipeline import run` 直接导入(src 布局 + editable 让"测试导不到包"的经典问题自动消失)。
- 用 `--import-mode=importlib`(已在 pyproject),**tests/ 不需要 `__init__.py`**。
- 测试专属 fixtures 放 `conftest.py`,不进 src/。
- beartype 违例在测试里会变成测试失败——这正是它帮你抓 bug 的方式。

**scripts/**

```bash
uv run python scripts/backfill.py
```

- 只用**绝对导入** `from myproj.X import Y`(scripts/ 不是包,别用相对导入)。
- 脚本是入口层:开头调一次 `setup_logging()`(§7.4 的日志纪律)。
- 跑 scripts/ 里的散文件 OK(它一 import myproj 就装上 hook);但**包内**模块要用 `python -m myproj.cli`,别 `python src/myproj/cli.py`(§3)。

**notebooks/**

```bash
uv run jupyter lab       # kernel 跑在装了 myproj 的环境里
```

第一格开 autoreload,改 src/ 不用重启 kernel:

```python
%load_ext autoreload
%autoreload 2
from myproj.core.logging import setup_logging
setup_logging()
```

之后 `from myproj.X import Y` 正常用。notebook 只做探索/可视化,**别在里面攒可复用逻辑**;值得留的代码重构进 src/。

### 7.9 结构的可导航性:domain-first 分层

**命名即路径**——让 agent 由名字直接定位代码,是结构层面的"机器友好",与类型在接口层面的作用对应。"修 reranker"应当无需搜索就能推断到 `retrieval/reranking/`。

- **domain-first,不 layer-first**:按能力/领域分包(`retrieval/`、`ingestion/`),不要按技术种类平铺(所有模型塞 `models/`、所有杂项塞 `utils/`)。前者随规模扩展、名字直接指向位置。
- **可嵌套到 3–4 层**:`src/<pkg>/<domain>/<subdomain>/<module>.py`。别为深而深——叶子模块要有实质内容,避免每层只有一个文件的"洋葱"。
- **叶子包形状一致**:每个领域叶子包可含 `models.py`(该领域的 pydantic 契约)、实现模块、`__init__.py`(thin re-export 公共 API)。这样 agent 在任何包内都知道去哪找。
- **数据契约的位置**:跨领域共享的 pydantic 模型放顶层 `schemas/`;领域私有的放该领域包内 `models.py`。
- **`core/` 只放基础设施**(settings/logging/paths/prompts),不掺业务。
- **__init__ 与 beartype**:深化后**只有 `core/__init__.py`(以及从顶层 `__init__.py` 到 settings 路径上的任何包)必须为空**;其余子包 `__init__.py` 在 hook 之后导入,可以 re-export 公共 API——这反而**助于导航**(`from myproj.retrieval import Reranker`)。

示例(RAG/agent,按需裁剪):

```
src/myproj/
├── __init__.py              # beartype hook
├── core/                    # 跨切面基础设施(非业务)
│   ├── __init__.py          #   空
│   ├── settings.py  paths.py  logging.py  prompts.py
├── prompts/                 # 提示词资源(随包出厂)
│   └── rag/answer.md
├── schemas/                 # 跨领域共享的 pydantic 数据契约
│   ├── documents.py  retrieval.py
├── ingestion/               # 领域:文档摄入
│   ├── parsing/  chunking/  embedding/
├── retrieval/               # 领域:检索
│   ├── vector/  reranking/  fusion/
├── generation/              # 领域:生成
│   ├── llm/  synthesis/
├── agents/                  # 领域:agent 编排
│   ├── tools/  orchestration/
├── pipelines/               # 端到端管道组装
├── api/                     # 对外接口(FastAPI 等)
└── cli.py                   # 入口
```

---

## 8. Agent 工作流

```
写/改代码
  → 跑 §1 的单条命令
  → 解析机器可读错误(ruff / mypy / pytest+beartype)
  → 定位修复
  → 重复直到全绿
  → 提交
```

- 该命令是 agent 唯一的正确性判据。
- CI 用 `On` 全量 beartype + Hypothesis 作为最后一道严格门。
- 多 agent 协作时质量门一致;任何 agent 的产出都要过这条命令才算完成。

---

## 9. 模型无关:把每个 AI 依赖收敛成一个可热插拔的缝

模型是可热插拔的商品。一旦正确性依赖某个具体模型的输出,你就和它联姻——把正确性、可测性、可审计性从模型里抽出来,钉死在确定性代码上。

- **每个外部依赖 = 一个最小 Protocol(`ports/protocols.py`)。** LLM/embedding/reranker/向量库/解析器各一个窄接口;核心与领域代码只依赖 `ports/`,**import 厂商 SDK 数为 0**(`check_conformance.py` 会 grep 强制)。接口越窄能塞的实现越多,"换模型"从重构降级为加一个类。
- **唯一装配缝(`ports/factory.py`)按 env 选实现并注入。** 业务代码不写裸厂商名,只调 `make_llm()`;未知配置显式抛错。
- **SDK 只在 `adapters/`,且 lazy import,厂商异常归一到 `ProviderError`。** 厂商包进可选 extras;网络/超时/API 错包成自有边界异常,程序错(KeyError/TypeError)照常上抛——**严禁 `except Exception` 把所有错塞进降级路径**。
- **MockProvider 作 default(不是测试桩)。** 不装 SDK、不连网也能跑通主链路并通过测试;CI 快、稳、免费、不被随机性污染。"无 key 也能 demo/test 跑绿"设成硬性验收(`tests/test_smoke.py`)。
- **一致性契约(conformance kit,`tests/test_conformance.py`)把所有实现绑死在同组不变量上。** 任何号称实现了某 Protocol 的类(Mock 与真实后端)都跑同一组行为契约——可插拔只在"所有插头行为一致"时才安全,否则 bug 以"换了模型后偶发"出现。

## 10. 让 AI 输出可信:把约束下沉到控制流,而非写进 Prompt

Prompt 是软约束,温度/越狱/长上下文都能绕过;只有沉到代码的约束,才能从"概率性遵守"变成"结构上不可能违反"。本节偏原则(不像结构那样能完全机械检验),但对 AI-touching 代码是上位纪律。

- **Constrain, don't ask。** 对不可妥协的属性(不编造、必引用、不越权),让模型物理上无法违反:命中事实时答案由代码从结构化值确定性合成、模型散文整段丢弃;无事实时编排层改写成"查不到"。迁移:列"绝不能发生"清单,逐条问"模型能否在听话的同时仍违反它",凡"能"的就移出模型。
- **收窄发射面。** 不让模型自由生成关键载荷:让它在受控选项里选、调用返回三态(found/not_found/unrecognized)的工具,最终数字一律取自工具结果而非模型文本。模型能犯的错与它能输出的"面积"成正比。
- **安全门确定性、独立、永不可插拔。** 理解类(意图解析)可插拔;安全决策(越权/敏感隔离)做成确定性代码门,从原始输入独立重判,不信任可插拔组件的输出。可替换的是智能,不是护栏。
- **血缘进、隐私出(`core.logging.log_provenance` + `SENSITIVE_FIELDS`)。** 每条产出带来源 + 产出它的实现/版本号(多实现可并存可审计);trace 只记码值/计数/耗时,绝不落答案/数值/原文。

## 11. 把人类的隐性兜底外化成会失败的工件

人靠经验、记忆、羞耻感判断"做完没""文档过时没";agent 没有这些,只优化能观测到的反馈。每加一个会失败的检查,就把一份隐性知识变成 agent 无法悄悄绕过的硬约束。

- **加宽的零警告门(`ci.sh`)。** 一条 `set -euo pipefail` 脚本串起:ruff + mypy `--strict` + 文档漂移 + beartype On 测试 + 冒烟 + **warnings-as-errors**(pytest `filterwarnings=["error"]`);任一项非零即没完成。人和 agent 共用同一条判据,用 pre-push hook 钉死。
- **漂移守卫(`scripts/check_drift.py`)。** 描述代码的文档带 `covers:` 元数据,被覆盖的路径失效即 CI 红——AI 开发最大的隐性成本是"上下文骗了它",给输入端装真实性保险丝。可扩展到符号级反射(改名/删除即红)。
- **自描述工件从真实代码派生。** 架构/拓扑图从真实接线内省派生而非手画;手维护的图必然腐烂,而腐烂的图比没有更危险——会自信地误导后续 agent。
- **分层上下文,而非一份大文档读到底(`CLAUDE.md`)。** 根级只放"路由表"(硬约束 + 去哪找)、领域子树放就近的简短契约、深挖文档靠 grep、生成物单独成区并 git-ignore。上下文窗口稀缺,"什么都塞"稀释信号。

## 12. 驾驭 AI 做大工作:可拆分、可逐步验证、可对抗审查

把 AI 当可监督的劳力,而非无监督的自动驾驶。这是工作流层(可作姊妹技能),轻量版规则:

- **先决策再编码(ADR,`docs/adr/`)。** 架构/产品决策写成编号、不可变的 ADR(背景 + 选定 + 被否决备选及理由),AI 只在锁定边界内填空。AI 最擅长明确约束下填实现,最不可靠的是替你做含糊取舍;否决理由还防它重走已排除的路。
- **TDD 红灯先行,测试即不可动摇的规格。** 每个改动先写会失败的测试再实现到绿,**绝不为通过而弱化测试**;给 subagent 的任务直接附上失败测试作为验收。
- **拆成编号步骤、每步独立绿灯。** 大重构拆成有序步骤,每步一次提交、跑完整门禁再进入下一步,绝不攒巨型 diff——把失败爆炸半径压到一步之内。
- **分解→并行→综合,主审者把关每个 diff。** 主 agent 拆出边界清晰、规格完整的子任务并行分派,逐个审查 diff 并在提交前跑门禁。
- **对抗式独立复审:用怀疑的 AI 查 AI。** 写完后另起独立、带敌意的多视角复审(明确"假设它有错,去证伪"),优先审无法被测试覆盖的产物(图、文档、取舍)——同一 agent 既写又夸会系统性确认偏差。

---

## 附录:配置与样板

> 依赖:`uv add pydantic "pydantic-settings[yaml]" beartype jinja2`;`uv add --dev mypy ruff pytest hypothesis`。
> v2 里 `BaseSettings` 在独立的 **pydantic-settings** 包;`[yaml]` extra 引入 PyYAML 以支持 `configs/*.yaml`。
> 确保 beartype / pydantic 为支持 **Python 3.13** 的版本。
> 一次性安装本项目自身(editable):`uv sync`;之后改 src/ 即时生效,只有改依赖才需重新同步。

### `pyproject.toml`

```toml
[project]
name = "myproj"
requires-python = ">=3.13"
dependencies = ["pydantic", "pydantic-settings[yaml]", "beartype", "jinja2"]

[project.optional-dependencies]
dev = ["mypy", "ruff", "pytest", "hypothesis"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/myproj"]
# hatchling 默认把包目录下的非 .py 文件(如 prompts/*.md)一并打进 wheel,无需额外配置

[tool.mypy]
python_version = "3.13"
strict = true
warn_unreachable = true

[tool.ruff]
target-version = "py314"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "ANN", "B", "SIM", "RUF"]

[tool.pytest.ini_options]
addopts = "-q --import-mode=importlib"
testpaths = ["tests"]
```

### `src/myproj/__init__.py`

```python
"""包初始化:在导入任何子模块之前,按配置安装 beartype 运行时类型检查。

claw hook 只对其安装之后导入的模块生效,所以本文件必须最先执行;
hook 之前只能导入 settings(叶子)——不要导入任何想被检查的一方模块。
"""
import os

from .core.settings import settings  # 叶子;有意在 hook 之前导入(本身不被检查)

if settings.beartype_on:
    from beartype import BeartypeConf, BeartypeStrategy
    from beartype.claw import beartype_this_package

    # CI:全量 O(n) 抓干净;本地:O(1) 抽样保持快反馈
    _strategy = BeartypeStrategy.On if os.getenv("CI") else BeartypeStrategy.O1
    beartype_this_package(conf=BeartypeConf(strategy=_strategy))

# ↓ 其它包级导入/导出一律放在 hook 之后
```

### `src/myproj/core/__init__.py`

```python
# 必须保持空。
# 导入 settings(叶子)会先经过本文件;若在此 re-export paths / logging / prompts,
# 它们会在 beartype claw hook 安装前被导入,从而漏掉运行时类型检查。
```

### `src/myproj/core/settings.py`

```python
"""全局配置与环境变量的唯一来源:环境变量 + .env + configs/settings.yaml。

beartype 叶子约束:本模块不得 import 任何本项目内、希望被检查的模块。
只依赖标准库 + pydantic / pydantic-settings(第三方依赖不受叶子约束限制)。
"""
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


def _find_project_root() -> Path:
    """向上找 pyproject.toml 作为项目根,仅用于 dev 下 CWD 无关的默认路径。

    找不到(如非 editable 的 wheel 部署)则退回当前工作目录;
    部署应以环境变量(APP_*)显式指定路径,不依赖此函数。
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return Path.cwd()


_ROOT = _find_project_root()


# —— 复杂全局变量用嵌套模型表达,yaml / env 都能填 ——
class RetrieverConfig(BaseModel):
    top_k: int = 5
    rerank_model: str = "cohere/rerank-v4.0-fast"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",                  # APP_IS_DEBUG、APP_BEARTYPE_ON ...
        env_nested_delimiter="__",          # APP_RETRIEVER__TOP_K 覆盖嵌套字段
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file=_ROOT / "configs" / "settings.yaml",
        extra="ignore",
    )

    is_debug: bool = False              # 日志级别、prompt 缓存等(与 beartype 解耦)
    beartype_on: bool = True            # 运行时类型检查总开关;仅生产设 APP_BEARTYPE_ON=false

    # 运行期可写目录(默认锚定项目根;部署可用 APP_*_DIR 覆盖)
    data_dir: Path = _ROOT / "data"
    log_dir: Path = _ROOT / "logs"

    # 复杂结构化配置(来自 configs/settings.yaml,可被 env 覆盖)
    retriever: RetrieverConfig = RetrieverConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # 优先级从高到低:构造参数 > 环境变量 > .env > yaml > secrets
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


settings = Settings()
```

### `configs/settings.yaml`

```yaml
# 结构化全局配置;环境变量(APP_*)可逐项覆盖,如 APP_RETRIEVER__TOP_K=20
retriever:
  top_k: 10
  rerank_model: cohere/rerank-v4.0-fast
```

### `src/myproj/core/prompts.py`

```python
"""提示词加载轮子:从包内 prompts/ 读取与渲染,供其他代码调用。

提示词随包出厂(src/<pkg>/prompts/<name>.md),用 PackageLoader 定位,
dev(editable)与生产(wheel)行为一致,不依赖 CWD 或项目根。
约定:render_prompt("rag/answer", ...) 对应 <pkg>/prompts/rag/answer.md。
"""
from jinja2 import Environment, PackageLoader, StrictUndefined

from .settings import settings

_PKG = __name__.split(".")[0]  # 顶层包名,重命名安全
_loader = PackageLoader(_PKG, "prompts")
_env = Environment(
    loader=_loader,
    undefined=StrictUndefined,                      # 缺变量直接报错,而非静默空串
    autoescape=False,                               # 提示词不是 HTML
    cache_size=0 if settings.is_debug else 400,     # dev 不缓存,改了即时生效
)


def render_prompt(name: str, /, **variables: object) -> str:
    """渲染带 Jinja2 变量的提示词;缺变量会报错。"""
    return _env.get_template(f"{name}.md").render(**variables)


def get_prompt(name: str) -> str:
    """读取原始提示词文本(无变量场景)。"""
    source, _, _ = _loader.get_source(_env, f"{name}.md")
    return source
```

### `src/myproj/core/paths.py`

```python
"""类型化路径。两类分开:

- 包内自带资源(随发行物出厂的只读文件):用 importlib.resources 定位。
- 运行期可写目录(data/logs):从 settings 取,不写在包代码旁边。
"""
from importlib.resources import files
from pathlib import Path

from .settings import settings

_PKG = __name__.split(".")[0]  # 顶层包名,重命名安全

DATA_DIR: Path = settings.data_dir
LOG_DIR: Path = settings.log_dir


def resource_path(relative: str) -> Path:
    """包内自带资源的路径(假设文件系统安装,如 Docker/服务器部署)。

    zip 安装场景请改用 importlib.resources.as_file 上下文管理器。
    """
    return Path(str(files(_PKG))) / relative
```

### `src/myproj/core/logging.py`

```python
"""日志配置的唯一来源。

纪律:库代码(src/ 内)只 `logging.getLogger(__name__)`,
绝不在本模块之外配置日志(不 basicConfig、不加 handler、不在 import 时配置)。
`setup_logging()` 由入口在启动时调用一次,幂等。
"""
import logging
from logging.config import dictConfig

from .settings import settings

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    level = "DEBUG" if settings.is_debug else "INFO"
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}
            },
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "default"}
            },
            "root": {"handlers": ["console"], "level": level},
        }
    )
    _configured = True
```

### `Makefile`(或 justfile)

```makefile
check:                    # agent 每次改动后跑这条
	ruff format --check .
	ruff check .
	mypy .
	CI=1 pytest           # CI=1 → beartype 走 On 全量检查

dev-test:                 # 本地快速迭代:beartype 走 O1
	pytest

fmt:
	ruff format .
	ruff check --fix .
```

- 生产部署:设 `APP_BEARTYPE_ON=false`,beartype 完全不挂载,零开销。
- 边界安全(LLM/外部输入)始终由 §4 的 pydantic 兜底,与上述开关无关。
