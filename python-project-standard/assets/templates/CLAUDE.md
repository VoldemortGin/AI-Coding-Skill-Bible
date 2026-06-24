# __PACKAGE_NAME__ — AI 开发约束(常驻)

> 本文件是根级**路由表**:只放硬约束 + 去哪找。领域细节就近放各 `src/__PACKAGE_NAME__/<domain>/` 下的简短契约,不在此堆叠。

## 不可违反(违反即破坏设计)
- mypy `--strict`,禁裸 `Any`;PEP 695 写法;Python 3.13。
- 运行时类型:beartype 经 `settings.beartype_on` + claw hook(包 `__init__.py` 顶部);`core/__init__.py` 必须空、`core/settings.py` 是叶子。
- 边界用 pydantic 校验。外部 AI 依赖只经 `ports/` 的 Protocol;SDK 只在 `adapters/`;核心与领域代码**零 SDK import**。
- 安全/正确性下沉到确定性代码,不写进 prompt。安全门确定性、独立、不可插拔。
- 完成 = 一条门绿:`./ci.sh`(ruff + mypy + 漂移 + beartype On 测试 + 冒烟,零警告)。这是唯一判据,不许"看着没问题就提交"。
- 任何可复用逻辑进 `src/`;domain-first 深结构,命名即定位。

## 流程
- 方向先写 `docs/adr/`(编号、不可变:背景 + 选定 + 被否决备选及理由)再编码。
- TDD:先写会失败的测试(即规格),再实现到绿,**绝不弱化测试**。
- 大改拆编号步骤,每步过 `./ci.sh` 再下一步,不攒巨 diff。
- 写完另起**独立、带敌意**的复审(假设它有错去证伪),优先审测试盖不到的图/文档/取舍。

## 去哪找
- 完整标准与 rationale:skill 的 `references/standard.md`。
- 各领域契约:`src/__PACKAGE_NAME__/<domain>/README.md`(就近)。
