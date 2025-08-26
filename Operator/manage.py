from Agent.WriteAgent import WriterAgent
from Agent.CharacterAgent import CharacterAgent
from agent.DecicionAgent import DecisionAgent
from Agent.MemoryAgent import MemoryAgent

class Manage:
    """
    Manage 类用于统一管理和调度各类 Agent，包括创建 Agent 实例和调用 Agent 功能。
    """

    def __init__(self):
        """
        初始化 Manage 实例，维护一个 Agent 字典。
        """
        self.agents = {}

    def create_agent(self, name: str, agent_type: str, *args, **kwargs):
        """
        创建指定类型的 Agent 实例并存储到管理器中。
        :param name: Agent 的唯一标识名
        :param agent_type: Agent 类型字符串（WriterAgent、CharacterAgent、DecisionAgent、MemoryAgent）
        :param args: Agent 初始化参数
        :param kwargs: Agent 初始化参数
        """
        agent_classes = {
            "WriterAgent": WriterAgent,
            "CharacterAgent": CharacterAgent,
            "DecisionAgent": DecisionAgent,
            "MemoryAgent": MemoryAgent
        }
        agent_class = agent_classes.get(agent_type)
        if not agent_class:
            raise ValueError(f"未知的 Agent 类型: {agent_type}")
        agent = agent_class(*args, **kwargs)
        self.agents[name] = agent
        return agent

    def call_agent(self, name: str, method: str, *args, **kwargs):
        """
        调用指定 Agent 的方法。
        :param name: Agent 的唯一标识名
        :param method: 要调用的方法名
        :param args: 方法参数
        :param kwargs: 方法参数
        :return: 方法调用结果
        """
        agent = self.agents.get(name)
        if not agent:
            raise ValueError(f"Agent '{name}' 不存在")
        func = getattr(agent, method, None)
        if not func:
            raise AttributeError(f"Agent '{name}' 没有方法 '{method}'")