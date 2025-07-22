from autogen_agentchat.agents import AssistantAgent
from Resource.template.storygen_prompt.shortgoal import shortgoal_prompt_template
from Resource.template.storygen_prompt.longgoal import longgoal_prompt_template




def create_agents(model_client):

    shortgoal_agent = AssistantAgent(
            name="shortgoal_agent",
            description="生成短期目标，即当前任务的目标",
            client=model_client,
            system_message= shortgoal_prompt_template
        )
    
    longgoal_agent = AssistantAgent(
            name="long_goal_agent",
            description="用于判断当前方案是否实现长期目标",
            system_message=longgoal_prompt_template
        )


    return {
        "shortgoalAgent": shortgoal_agent,
        "longgoalAgent": longgoal_agent
    }