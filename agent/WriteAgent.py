from autogen_agentchat.agents import AssistantAgent
from Agent.MemoryAgent import MemoryAgent
from Resource.template.struct_init import demand_template, init_info_template
from collections import deque
from Resource.template.init_prompt.extractor import extractor_prompt_template
from Resource.template.init_prompt.validator import validator_prompt_template
from Resource.template.init_prompt.structurer import structurer_prompt_template
from Resource.template.init_prompt.initializer import initializer_prompt_template



def create_agents(model_client):

    memoryAgent = MemoryAgent

    recallAgent = AssistantAgent(
        name="recallAgent",
        model_client=model_client,
        system_message= extractor_prompt_template
    )

    diggerAgent = AssistantAgent(
        name="diggerAgent",
        model_client=model_client,
        system_message=validator_prompt_template
    )

    combiner = AssistantAgent(
        name="combinerAgent",
        model_client=model_client,
        system_message=structurer_prompt_template
    )

    writer = AssistantAgent(
        name="writerAgent",
        model_client=model_client,
        system_message=initializer_prompt_template
    )

    recall_search = AssistantAgent(
        name="recall_search",
        model_client=model_client,
        system_message=demand_template
    )

    digger_search = AssistantAgent(
        name="digger_search",
        model_client=model_client,
        system_message=init_info_template
    )

    return {
        "memAgnt": memoryAgent,
        "recallAgent": recallAgent,
        "diggerAgent": diggerAgent,
        "combiner": combiner,
        "writer": writer,
        "recall_search": recall_search,
        "digger_search": digger_search
    }