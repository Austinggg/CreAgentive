from autogen_agentchat.agents import AssistantAgent
from Resource.template.storygen_prompt.Eng.longgoal import longgoal_prompt_template
from Resource.template.storygen_prompt.Eng.shortgoal import SHORTGOAL_AGENT_PROMPT_TEMPLATE
from Resource.template.storygen_prompt.Eng.decision import decision_prompt_template


def create_agents(model_client):
    """
    Create and return story generation agents with specified roles and prompts.

    Args:
        model_client: The client used for model communication.

    Returns:
        A dictionary containing the created short-term and long-term goal agents.
    """
    shortgoal_agent = AssistantAgent(
        name="shortgoal_agent",
        description="Generates short-term goals, i.e., objectives for the current task",
        model_client=model_client,
        system_message=SHORTGOAL_AGENT_PROMPT_TEMPLATE
    )

    longgoal_agent = AssistantAgent(
        name="long_goal_agent",
        model_client=model_client,
        description="Evaluates whether the current plan achieves the long-term goal",
        system_message=longgoal_prompt_template
    )

    # decision_agent = AssistantAgent(
    #     name="decision_agent",
    #     model_client=model_client,
    #     description="Responsible for making decision evaluations during story generation",
    #     system_message=decision_prompt_template
    # )

    return {
        "shortgoalAgent": shortgoal_agent,
        "longgoalAgent": longgoal_agent
    }