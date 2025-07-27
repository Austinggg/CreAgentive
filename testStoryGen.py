from Workflow.StoryGen_wk import StoryGenWorkflow
import asyncio
from Resource.llmclient import LLMClientManager

# 初始化模型客户端
model_client = LLMClientManager().get_client("deepseek-v3")
storygenworkflow = StoryGenWorkflow(model_client, maxround=1) # 故事生成工作流

# 测试运行工作流
asyncio.run(storygenworkflow.run())
