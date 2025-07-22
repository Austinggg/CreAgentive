def extract_last_text_content(data: list) -> str:
    """
    提取列表中最后一个类型为 TextMessage 的 content 字段
    适用于：
    提取 Autogen 的 agent.run() 中llm 的答案
    提取 Autogen 的 team.run() 中llm 的答案

    
    Args:
        data (list): 包含多个字典对象的列表
        
    Returns:
        str: 最后一个 TextMessage 的 content 内容，若未找到则返回空字符串
    """
    # 逆序遍历列表
    for item in reversed(data):
        if item.get("type") == "TextMessage":
            return item.get("content", "")
    return ""