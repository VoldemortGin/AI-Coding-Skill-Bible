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
