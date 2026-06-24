"""唯一装配缝:按 settings 选实现并注入。默认 mock,未知配置显式抛错。

业务代码不写裸厂商名,只调 make_*();切换实现 = 改一个 env。
"""
from ..adapters.mock import MockEmbedder, MockLLM
from ..core.settings import settings
from .protocols import Embedder, LLM


def make_llm() -> LLM:
    match settings.llm_provider:
        case "mock":
            return MockLLM()
        case "openai":
            from ..adapters.openai_llm import OpenAILLM  # lazy import SDK
            return OpenAILLM()
        case other:
            raise ValueError(f"未知 llm_provider: {other!r}")


def make_embedder() -> Embedder:
    match settings.embedder_provider:
        case "mock":
            return MockEmbedder()
        case other:
            raise ValueError(f"未知 embedder_provider: {other!r}")
