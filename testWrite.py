import asyncio
from dotenv import load_dotenv
from Resource.llmclient import LLMClientManager
import os
from Workflow.Writing_wk import WritingWorkflow

# 加载环境变量
load_dotenv()


async def main():
    # 配置路径
    # project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chapters_dir = os.path.join("Resource", "memory", "story_plan")

    # 获取模型客户端和Neo4j密码
    llm_client = LLMClientManager().get_client("deepseek-v3")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    # 初始化并运行工作流
    workflow = WritingWorkflow(model_client=llm_client)
    await workflow.run(article_type="novel")  # 可切换为"script"


asyncio.run(main())
