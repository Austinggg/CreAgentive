from autogen_agentchat.agents import AssistantAgent
from Resource.template.storygen_prompt.longgoal import longgoal_prompt_template
from Resource.template.storygen_prompt.shortgoal import shortgoal_prompt_template
from Resource.template.storygen_prompt.decision import decision_prompt_template


def create_agents(model_client):
    shortgoal_agent = AssistantAgent(
        name="shortgoal_agent",
        description="生成短期目标，即当前任务的目标",
        model_client=model_client,
        system_message=shortgoal_prompt_template
    )

    longgoal_agent = AssistantAgent(
        name="long_goal_agent",
        model_client=model_client,
        description="用于判断当前方案是否实现长期目标",
        system_message=longgoal_prompt_template
    )

    # decision_agent = AssistantAgent(
    #     name="decision_agent",
    #     model_client=model_client,
    #     description="负责在故事生成过程中做出决策评分",
    #     system_message=decision_prompt_template
    # )

    return {
        "shortgoalAgent": shortgoal_agent,
        "longgoalAgent": longgoal_agent,
        "decisionAgent": decision_agent
    }
