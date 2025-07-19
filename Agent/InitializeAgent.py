from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from Resource.template.struct_init import demand_template, init_info_template
from collections import deque
from Resource.template.init_prompt.extractor import extractor_prompt_template
from Resource.template.init_prompt.validator import validator_prompt_template
from Resource.template.init_prompt.structurer import structurer_prompt_template
from Resource.template.init_prompt.initializer import initializer_prompt_template

# 自动化输入函数（测试用）
def automated_input_func(prompt):
    if not hasattr(automated_input_func, "test_inputs"):
        print("\n[自动化测试]: 没有更多预设输入。退出或提供空字符串。")
        return ""
    next_input = automated_input_func.test_inputs.popleft()
    print(f"\n[自动化测试]: 模拟用户输入: {next_input}")
    return next_input

def set_automated_input(test_inputs: deque):
    automated_input_func.test_inputs = test_inputs


def create_agents(model_client, test_inputs=None):
    if test_inputs:
        set_automated_input(test_inputs)

    user_proxy = UserProxyAgent(name="user_input", input_func=automated_input_func)

    extractor = AssistantAgent(
        name="extractor",
        description="一个需求提取助手，负责从用户输入中提取需求模板。",
        model_client=model_client,
        system_message= extractor_prompt_template
    )

    validator = AssistantAgent(
        name="validator",
        description="一个需求验证助手，负责检查当前模板是否完整（所有字段非 None）。",
        model_client=model_client,
        system_message=validator_prompt_template
    )

    structurer = AssistantAgent(
        name="structurer",
        description="一个需求结构化助手，负责将用户需求模板转化为结构化数据。",
        model_client=model_client,
        system_message=structurer_prompt_template
    )

    initializer = AssistantAgent(
        name="initializer",
        description="一个需求初始化助手，负责将用户需求转化为结构化数据。",
        model_client=model_client,
        system_message=initializer_prompt_template
    )

    return {
        "user_proxy": user_proxy,
        "extractor": extractor,
        "validator": validator,
        "structurer": structurer,
        "initializer": initializer
    }