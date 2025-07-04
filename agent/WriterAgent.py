from typing import AsyncGenerator, Sequence
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_core import CancellationToken

class WriterAgent(BaseChatAgent):
    """
    WriterAgent 基于 Autogen 框架，支持选择写作类型（小说或剧本），
    可在多智能体工作流中进行文本生成任务。
    """

    def __init__(self, name: str, client, writing_type: str = "novel"):
        super().__init__(name, "用于创意文本生成的智能体。")
        self.client = client
        self.writing_type = writing_type

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
        # 获取用户输入
        prompt = messages[-1].content if messages else ""
        if self.writing_type == "novel":
            full_prompt = f"请以小说的形式写作：{prompt}"
        elif self.writing_type == "script":
            full_prompt = f"请以剧本的形式写作：{prompt}"
        else:
            full_prompt = prompt

        # 调用大模型生成文本
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
