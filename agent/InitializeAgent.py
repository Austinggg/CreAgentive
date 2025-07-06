from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from resource.template.init import demand_template, init_info_template
from collections import deque

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
        model_client=model_client,
        system_message=(
            "你是一个结构化字段提取助手，从用户自然语言中提取并补充到下面的需求模板中。\n" +
            f"{demand_template} 这是当前需求模板的结构。\n" +
            "将这些字段存入模板中。未提到的不修改。"
        )
    )

    validator = AssistantAgent(
        name="validator",
        model_client=model_client,
        system_message=(
            "你是一个需求验证助手，负责检查当前模板是否完整（所有字段非 None）。\n" +
            "如果模板不完整，请针对缺失字段向用户提出明确的追问。\n" +
            "如果模板已完整，请只回复一个词：‘完整’。不要添加任何其他文字或标点符号。"
        )
    )

    structurer = AssistantAgent(
        name="structurer",
        model_client=model_client,
        system_message=(
            "你负责输出最终完整的需求模板，以需求模板的结构返回。\n" +
            f"{demand_template}"
        )
    )

    initializer = AssistantAgent(
        name="initializer",
        model_client=model_client,
        system_message=(
            "你是系统初始化助手，根据已完成的用户需求模板生成初始化配置。\n\n" +
            "请按照下面的初始始化信息模板（无需和用户交互）进行初始化：\n\n" +
            f"{init_info_template} \n\n" +
            "请确保生成的配置项符合需求模板的结构和内容要求。\n" +
            "注意生成的内容不要带有 markdown 格式或其他格式化标记。"
        )
    )

    return {
        "user_proxy": user_proxy,
        "extractor": extractor,
        "validator": validator,
        "structurer": structurer,
        "initializer": initializer
    }