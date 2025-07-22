from Resource.tools.extract_last_text_content import extract_last_text_content

def extract_llm_content(agent_result) -> str:
    """
    从 TaskResult 中提取最后一条来自智能体的文本消息
    """
    try:
        # 直接访问 TaskResult 的 messages 属性（非字典形式）
        messages = agent_result.messages if hasattr(agent_result, 'messages') else []
        # 逆序查找最后一条来自智能体的消息
        for msg in reversed(messages):
            if getattr(msg, 'source', '') in ('diggerAgent', 'recallAgent', 'combinerAgent'):
                return getattr(msg, 'content', '')
        return ""
    except Exception as e:
        print(f"⚠️ 提取LLM内容失败: {str(e)}")
        return ""
