from autogen_agentchat.agents import AssistantAgent
from Agent.MemoryAgent import MemoryAgent
from Resource.template.struct_init import demand_template, init_info_template
from Resource.template.init_prompt.extractor import extractor_prompt_template
from Resource.template.init_prompt.validator import validator_prompt_template
from Resource.template.init_prompt.structurer import structurer_prompt_template
from Resource.template.write_prompt.novel_writer import novel_write_prompt_template
from Resource.template.write_prompt.script_writer import script_write_prompt_template
from Resource.template.write_prompt.recallagent import recall_prompt_template
from Resource.template.write_prompt.digagent import dig_prompt_template
from Resource.template.write_prompt.combiner import combiner_prompt_template
import os



def create_agents(model_client):

    # 创建 MemoryAgent
    memoryAgent = MemoryAgent

    recallAgent = AssistantAgent(
        name="recallAgent",
        description="回忆 Agent，负责根据当前方案判断是否需要回溯前文的相关情节和背景信息",
        model_client=model_client,
        system_message= recall_prompt_template
    )

    diggerAgent = AssistantAgent(
        name="diggerAgent",
        description="挖坑 Agent，负责根据当前方案判断是否需要挖掘当前片段所缺失的必要信息",
        model_client=model_client,
        system_message=dig_prompt_template
    )

    combiner = AssistantAgent(
        name="combinerAgent",
        description="组合 Agent，负责将挖坑和 Recall 的结果与原方案进行组合，生成最终的方案",
        model_client=model_client,
        system_message=structurer_prompt_template
    )

    novel_writer = AssistantAgent(
        name="NovelwriterAgent",
        description="小说写作 Agent，负责将最终的方案进行写作，生成小说",
        model_client=model_client,
        system_message=novel_write_prompt_template
    )

    script_writer = AssistantAgent(
        name="ScriptwriterAgent",
        description="电影剧本写作 Agent，负责将最终的方案进行写作，生成电影剧本",
        model_client=model_client,
        system_message=script_write_prompt_template
    )

    recall_search = AssistantAgent(
        name="recall_search",
        description="回忆搜索 Agent，负责根据当前方案进行回忆相关情节和背景信息的搜索",
        model_client=model_client,
        system_message=recall_prompt_template
    )

    digger_search = AssistantAgent(
        name="digger_search",
        description="挖掘搜索 Agent，负责根据当前方案进行挖掘相关情节和背景信息的搜索",
        model_client=model_client,
        system_message=dig_prompt_template
    )

    return {
        "memAgnt": memoryAgent,
        "recallAgent": recallAgent,
        "diggerAgent": diggerAgent,
        "combiner": combiner,
        "novel_writer": novel_writer,
        "script_writer": script_writer,
        "recall_search": recall_search,
        "digger_search": digger_search
    }