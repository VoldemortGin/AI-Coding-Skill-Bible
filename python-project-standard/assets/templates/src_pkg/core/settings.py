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

    # provider 选择(唯一装配缝按 env 切换;默认 mock,离线/CI 可跑)
    llm_provider: str = "mock"
    embedder_provider: str = "mock"

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
