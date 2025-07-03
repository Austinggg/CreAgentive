class WriterAgent:
    """
    WriterAgent 类基于 Autogen 框架定义，是一个用于创意文本生成的智能体。
    该智能体用于在多智能体工作流中进行文本生成任务。
    """

    def __init__(self, client: str):
        """
        初始化 WriterAgent 实例，设置所用的模型客户端。
        :param client: 用于文本生成的大语言模型客户端
        """
        self.client = client

    def generate_text(self, prompt: str, max_tokens: int = 1024):
        """
        使用大语言模型根据输入 prompt 生成文本。
        :param prompt: 输入的提示词
        :param max_tokens: 生成文本的最大长度
        :return: 生成的文本内容
        """
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip() if response.choices else ""
