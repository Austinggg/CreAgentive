from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from Resource.template.struct_init import demand_template, init_info_template
from collections import deque
from Resource.template.init_prompt.Eng.extractor import extractor_prompt_template
from Resource.template.init_prompt.Eng.validator import validator_prompt_template
from Resource.template.init_prompt.Eng.structurer import structurer_prompt_template
from Resource.template.init_prompt.Eng.initializer import initializer_prompt_template


# Automated input function (for testing)
def automated_input_func(prompt):
    if not hasattr(automated_input_func, "test_inputs"):
        print("\n[Automated Test]: No more preset inputs. Exit or provide empty string.")
        return ""
    next_input = automated_input_func.test_inputs.popleft()
    print(f"\n[Automated Test]: Simulating user input: {next_input}")
    return next_input


def set_automated_input(test_inputs: deque):
    automated_input_func.test_inputs = test_inputs


def create_agents(model_client, test_inputs=None):
    if test_inputs:
        set_automated_input(test_inputs)

    user_proxy = UserProxyAgent(
        name="user_input",
        input_func=automated_input_func
    )

    extractor = AssistantAgent(
        name="extractor",
        description="A requirement extraction assistant responsible for extracting "
                    "requirement templates from user input.",
        model_client=model_client,
        system_message=extractor_prompt_template
    )

    validator = AssistantAgent(
        name="validator",
        description="A requirement validation assistant responsible for checking "
                    "whether the current template is complete (all fields are non-None).",
        model_client=model_client,
        system_message=validator_prompt_template
    )

    structurer = AssistantAgent(
        name="structurer",
        description="A requirement structuring assistant responsible for converting "
                    "user requirement templates into structured data.",
        model_client=model_client,
        system_message=structurer_prompt_template
    )

    initializer = AssistantAgent(
        name="initializer",
        description="A requirement initialization assistant responsible for converting "
                    "user requirements into structured data.",
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
