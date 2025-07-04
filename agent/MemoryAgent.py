from typing import AsyncGenerator, List, Sequence
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_core import CancellationToken

class MemoryAgent(BaseChatAgent):
    """
    MemoryAgent 基于 Autogen 框架，负责管理和存储智能体的记忆信息，
    并可调用大语言模型对记忆内容进行总结。
    """

    def __init__(self, name: str, client):
        super().__init__(name, "用于记忆管理的智能体。")
        self.client = client
        self.memory = []

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    def add_memory(self, content: str):
        """
        向记忆中添加一条内容。
        :param content: 要添加的记忆内容
        """
        self.memory.append(content)

    def get_memory(self):
        """
        获取所有记忆内容。
        :return: 记忆内容列表
        """
        return self.memory

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
        # 将当前记忆内容与用户输入结合
        full_prompt = "请结合以下记忆内容进行总结或回复：\n" + "\n".join(self.memory) + f"\n用户输入：{prompt}"
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
        self.memory = []