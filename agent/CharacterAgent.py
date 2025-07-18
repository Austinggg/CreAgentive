from typing import AsyncGenerator, Sequence
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_core import CancellationToken
from agent.MemoryAgent import MemoryAgent
import uuid


class CharacterAgent(BaseChatAgent):
    """
    CharacterAgent 基于 Autogen 框架定义，用于模拟具有特定角色设定的智能体。
    支持自定义角色信息和指定用于文本生成的 client。
    """

    def __init__(self, name: str, personality: str, gender: str, role: str, memory: str, relationships: str, client):
        """
        初始化 CharacterAgent 实例。

        :param name: 智能体的名称
        :param personality: 智能体的个性描述
        :param client: 用于文本生成的客户端实例
        """
        super().__init__(name=name, client=client)
        self.id = str(uuid.uuid4())
        self.personality = personality
        self.gender = gender
        self.tmp_memory = []
        self.state = {
            "role": role,
            "memory": memory,
            "relationships": relationships
        }
        

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken, chapter: int) -> Response:
        # response: Response | None = None
        # async for message in self.on_messages_stream(messages, cancellation_token):
        #     if isinstance(message, Response):
        #         response = message
        # assert response is not None
        # return response
        """从接受到的消息中分离有效内容，填入相关角色信息，并生成回复消息。
        :param messages: 接收到的消息列表
        :param cancellation_token: 取消令牌，用于中止操作
        :return: 生成的回复消息
        """
        name = self.name
        # 临时记忆，决策前产生的事件，不更新知识图谱但在本轮交互中需要使用，展示情节变化
        # 读取角色状态（读取知识图谱，获得相关信息）
        memory = MemoryAgent()
        character_memory = memory.get_character_memory(name, chapter)  # 假设章节
        # 生成回复内容
        prompt = messages[-1].content if messages else ""
        full_prompt = f"你现在是{self.name}，请以该角色的身份回复：{prompt},你所知道的信息是：{character_memory}。刚刚发生了{tmp_memory}"
        result = self.client.chat.completions.create(
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=4096
        )
        content = result.choices[0].message.content.strip() if result.choices else "生成失败"
        msg = TextMessage(content=content, source=name)
        # 生成回复
        response = Response(chat_message=msg, inner_messages=[msg])
        # 更新临时记忆
        self.tmp_memory.append(msg)
        return response

    async def on_messages_stream(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        prompt = messages[-1].content if messages else ""
        full_prompt = f"你现在是{self.description}，请以该角色的身份回复：{prompt}"
        result = self.client.chat.completions.create(
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=4096
        )
        content = result.choices[0].message.content.strip() if result.choices else "生成失败"
        msg = TextMessage(content=content, source=self.name)
        yield msg
        yield Response(chat_message=msg, inner_messages=[msg])

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        # 可选：重置 Agent 状态
        pass


    async def on_update(self, cancellation_token: CancellationToken) -> dict:
        # 更新知识图谱，加入新角色或角色信息变化
        character = {
            "id": self.id,
            "name": self.name,
            "personality": self.personality,
            "gender": self.gender,
            "state": self.state
        }
        return character
