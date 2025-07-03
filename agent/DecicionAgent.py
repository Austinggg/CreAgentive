class DecisionAgent:
    """
    DecisionAgent 类基于 Autogen 框架定义，用于决策任务的智能体。
    支持指定用于决策生成的大语言模型客户端。
    """

    def __init__(self, client):
        """
        初始化 DecisionAgent 实例，设置所用的模型客户端。
        :param client: 用于决策生成的大语言模型客户端
        """
        self.client = client

    def make_decision(self, prompt: str, max_tokens: int = 512):
        """
        使用大语言模型根据输入 prompt 生成决策建议。
        :param prompt: 输入的决策提示
        :param max_tokens: 生成文本的最大长度
        :return: 生成的决策内容
        """
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip() if response.choices else ""