"""示例真实 adapter:SDK 只在方法内 lazy import,厂商异常归一到 ProviderError。

openai 进可选 extras([project.optional-dependencies] openai);未选此 provider 不需要它。
"""
from ..ports.exceptions import ProviderError
from ..ports.protocols import LLM


class OpenAILLM:
    def complete(self, prompt: str, /) -> str:
        from openai import OpenAI, OpenAIError  # lazy:未装 SDK 则 ImportError(配置/环境错,响亮上抛)

        try:
            client = OpenAI()
            resp = client.responses.create(model="gpt-4o", input=prompt)
            return resp.output_text
        except OpenAIError as e:  # 仅厂商/网络错归一;程序错(TypeError 等)照常上抛
            raise ProviderError(f"OpenAI 调用失败: {e}") from e
