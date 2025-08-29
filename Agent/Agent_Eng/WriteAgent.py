from autogen_agentchat.agents import AssistantAgent
from Agent.Agent_Eng.MemoryAgent import MemoryAgent
from Resource.template.write_prompt.Eng.novel_writer import novel_write_prompt_template
from Resource.template.write_prompt.Eng.script_writer import script_write_prompt_template
from Resource.template.write_prompt.Eng.recallagent import recall_prompt_template
from Resource.template.write_prompt.Eng.digagent import dig_prompt_template
from autogen_core.model_context import UnboundedChatCompletionContext
import os
import json
from autogen_agentchat.messages import TextMessage


def create_agents(model_client):
    """
    Create and return all required agents.

    Args:
        model_client: The language model client.

    Returns:
        A dictionary containing all agents.
    """
    # Instantiate MemoryAgent (note: currently just referencing the class, not creating an instance)
    memory_agent = MemoryAgent

    # 1. Prepare initial messages (optional, can be extended based on business needs)
    initial_messages = []

    # 2. Directly instantiate UnboundedChatCompletionContext for each agent
    context_recall = UnboundedChatCompletionContext(initial_messages=initial_messages)
    context_digger = UnboundedChatCompletionContext(initial_messages=initial_messages)
    context_novel = UnboundedChatCompletionContext(initial_messages=initial_messages)
    context_script = UnboundedChatCompletionContext(initial_messages=initial_messages)

    # Create recall agent
    recall_agent = AssistantAgent(
        name="recallAgent",
        description="Recall agent responsible for determining whether relevant plot elements and background "
                    "from previous chapters need to be retrieved based on the current and prior chapter plans.",
        model_client=model_client,
        model_context=context_recall,
        system_message=recall_prompt_template,
    )

    # Create foreshadowing (digger) agent
    digger_agent = AssistantAgent(
        name="diggerAgent",
        description="Foreshadowing agent responsible for analyzing the current and subsequent chapters "
                    "to determine whether plot hooks or foreshadowing elements should be set.",
        model_client=model_client,
        model_context=context_digger,
        system_message=dig_prompt_template,
    )

    # Create novel writing agent
    novel_writer = AssistantAgent(
        name="NovelwriterAgent",
        description="Novel writing agent responsible for generating the final novel based on the given plan.",
        model_context=context_novel,  # Change model context type to support clearing
        model_client=model_client,
        system_message=novel_write_prompt_template,
    )

    # Create script writing agent
    script_writer = AssistantAgent(
        name="ScriptwriterAgent",
        description="Screenplay writing agent responsible for generating a movie script based on the final plan.",
        model_context=context_script,  # Change model context type to support clearing
        model_client=model_client,
        system_message=script_write_prompt_template,
    )

    def format_task(task):
        """
        Ensure the task data is in the correct format.
        If the task is a string, try to parse it as JSON; otherwise, wrap it in a dictionary.
        """
        if isinstance(task, str):
            try:
                task = json.loads(task)
            except json.JSONDecodeError:
                task = {"content": task}
        return task if isinstance(task, dict) else {"content": str(task)}

    # Wrapper for async run to ensure the task is always passed as a string
    def async_run_wrapper(agent, task):
        formatted_task = format_task(task)
        new_task = json.dumps(formatted_task, ensure_ascii=False)
        return agent.run(task=new_task)

    # Attach the wrapped async method to each agent
    recall_agent.a_run = lambda task: async_run_wrapper(recall_agent, task)
    digger_agent.a_run = lambda task: async_run_wrapper(digger_agent, task)
    novel_writer.a_run = lambda task: async_run_wrapper(novel_writer, task)
    script_writer.a_run = lambda task: async_run_wrapper(script_writer, task)

    # Return all required agents
    return {
        "memAgent": memory_agent,
        "recallAgent": recall_agent,
        "diggerAgent": digger_agent,
        "novel_writer": novel_writer,
        "script_writer": script_writer
        # Removed recall_search and digger_search as their functionality duplicates recallAgent/diggerAgent
    }