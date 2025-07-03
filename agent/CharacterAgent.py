

class CharacterAgent:
    """
    CharacterAgent 类基于 Autogen 框架定义，用于模拟具有特定角色设定的智能体。
    支持自定义角色信息和指定用于文本生成的 client。
    """

    def __init__(self, name: str, description: str, client):
        """
        初始化 CharacterAgent 实例。
        :param name: 角色名称
        :param description: 角色描述
        :param client: 用于文本生成的大语言模型客户端
        """
        self.name = name
        self.description = description
        self.client = client

    def introduce(self):
        """
        返回角色的自我介绍文本。
        :return: 自我介绍字符串
        """
        return f"大家好，我是{self.name}，{self.description}"

    def generate_text(self, prompt: str, max_tokens: int = 1024):
        """
        使用指定的 client 根据输入 prompt 生成文本。
        :param prompt: 输入的提示词
        :param max_tokens: 生成文本的最大长度
        :return: 生成的文本内容
        """
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip() if response.choices else ""