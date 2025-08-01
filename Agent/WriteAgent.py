from autogen_agentchat.agents import AssistantAgent
from Agent.MemoryAgent import MemoryAgent
from Resource.template.write_prompt.novel_writer import novel_write_prompt_template
from Resource.template.write_prompt.script_writer import script_write_prompt_template
from Resource.template.write_prompt.recallagent import recall_prompt_template
from Resource.template.write_prompt.digagent import dig_prompt_template
from autogen_core.model_context import UnboundedChatCompletionContext
# from autogen_core.model_context import ChatCompletionContext
import os
import json
from autogen_agentchat.messages import TextMessage
def create_agents(model_client):
    """
    创建并返回所有需要的智能体
    :param model_client: 语言模型客户端
    :return: 包含所有智能体的字典
    """
    # 实例化MemoryAgent
    memoryAgent = MemoryAgent

    # 1. 准备初始消息（可选，根据业务需求添加）
    initial_messages = []
    # 2. 直接实例化 UnboundedChatCompletionContext
    context_recall = UnboundedChatCompletionContext(initial_messages=initial_messages)
    context_digger = UnboundedChatCompletionContext(initial_messages=initial_messages)
    context_novel = UnboundedChatCompletionContext(initial_messages=initial_messages)
    context_script = UnboundedChatCompletionContext(initial_messages=initial_messages)

    # 创建回忆Agent
    recallAgent = AssistantAgent(
        name="recallAgent",
        description="回忆Agent，负责根据当前方案与先前章节方案，判断是否需要回溯前文的相关情节和背景信息",
        model_client=model_client,
        model_context=context_recall,
        system_message=recall_prompt_template,
    )

    # 创建挖坑Agent
    diggerAgent = AssistantAgent(
        name="diggerAgent",
        description="挖坑Agent，负责分析当前章节与后续章节，判断是否需要设置伏笔",
        model_client=model_client,
        model_context=context_digger,
        system_message=dig_prompt_template,
    )

    # 创建小说写作Agent
    novel_writer = AssistantAgent(
        name="NovelwriterAgent",
        description="小说写作Agent，负责将最终的方案进行写作，生成小说",
        model_context= context_novel, # 更改模型的上下文类型，支持清空
        model_client=model_client,
        system_message=novel_write_prompt_template,
    )

    # 创建剧本写作Agent
    script_writer = AssistantAgent(
        name="ScriptwriterAgent",
        description="电影剧本写作Agent，负责将最终的方案进行写作，生成电影剧本",
        model_context= context_script, # 更改模型的上下文类型，支持清空
        model_client=model_client,
        system_message=script_write_prompt_template,
    )

    def format_task(task):
        """确保任务数据格式正确"""
        if isinstance(task, str):
            try:
                task = json.loads(task)
            except json.JSONDecodeError:
                task = {"content": task}
        return task if isinstance(task, dict) else {"content": str(task)}

    # 修改异步调用包装器
    def async_run_wrapper(agent, task):
        # 确保任务始终为字典格式，避免字符串直接传入
        formatted_task = format_task(task)
        # 使用json.dumps将字典转为字符串，确保类型正确
        return agent.run(task=json.dumps(formatted_task))  # 新增此行转换

    recallAgent.a_run = lambda task: async_run_wrapper(recallAgent, task)
    diggerAgent.a_run = lambda task: async_run_wrapper(diggerAgent, task)
    novel_writer.a_run = lambda task: async_run_wrapper(novel_writer, task)
    script_writer.a_run = lambda task: async_run_wrapper(script_writer, task)
    # 返回所有需要的Agent
    return {
        "memAgent": memoryAgent,
        "recallAgent": recallAgent,
        "diggerAgent": diggerAgent,
        "novel_writer": novel_writer,
        "script_writer": script_writer
        # 移除了recall_search和digger_search，因为它们的功能与recallAgent/diggerAgent重复
    }
