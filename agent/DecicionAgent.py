from typing import AsyncGenerator, Sequence
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_core import CancellationToken


class DecisionAgent(BaseChatAgent):
    """
    DecisionAgent 基于 Autogen 框架定义，用于决策任务的智能体。
    支持指定用于决策生成的大语言模型客户端。
    """

    def __init__(self, name: str, client):
        super().__init__(name, "用于决策生成的智能体。")
        self.client = client

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        response: Response | None = None
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                response = message
        assert response is not None
        return response

    async def on_messages_stream(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        prompt = messages[-1].content if messages else ""
        full_prompt = f"请根据以下信息做出决策建议：{prompt}"
        result = self.client.chat.completions.create(
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=512
        )
        content = result.choices[0].message.content.strip() if result.choices else "生成失败"
        msg = TextMessage(content=content, source=self.name)
        yield msg
        yield Response(chat_message=msg, inner_messages=[msg])

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        # 可选：重置 Agent 状态
        pass