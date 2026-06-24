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
