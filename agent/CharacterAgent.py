from typing import AsyncGenerator, Sequence
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_core import CancellationToken

class CharacterAgent(BaseChatAgent):
    """
    CharacterAgent 基于 Autogen 框架定义，用于模拟具有特定角色设定的智能体。
    支持自定义角色信息和指定用于文本生成的 client。
    """

    def __init__(self, name: str, description: str, client):
        super().__init__(name, f"角色设定：{description}")
        self.description = description
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
        full_prompt = f"你现在是{self.description}，请以该角色的身份回复：{prompt}"
        result = self.client.chat.completions.create(
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=1024
        )
        content = result.choices[0].message.content.strip() if result.choices else "生成失败"
        msg = TextMessage(content=content, source=self.name)
        yield msg
        yield Response(chat_message=msg, inner_messages=[msg])

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        # 可选：重置 Agent 状态
        pass