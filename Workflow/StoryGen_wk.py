from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from Agent.InitializeAgent import create_agents, set_automated_input
import os
import json
from datetime import datetime
import asyncio
from Resource.tools.customJSONEncoder import CustomJSONEncoder
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock

class StoryGenWorkflow:
    def __init__(self, model_client):
        self.model_client = model_client
        