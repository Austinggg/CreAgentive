import os
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient
# from autogen_core.models import UserMessage
# import asyncio

class LLMClientManager:
    """
    LLMClientManager 封装了多种 LLM 客户端的初始化与获取方法。
    可通过 get_client(model_name) 获取指定模型的客户端实例。
    """

    def __init__(self):
        load_dotenv()
        siliconflow_api_key = os.getenv("SILICONFLOW_API_KEY") # 修改你的 API Key 环境变量名
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY") # openrouter api key

        # 初始化各类模型客户端
        self.clients = {
            "deepseek-v3": OpenAIChatCompletionClient(
                model="deepseek-ai/DeepSeek-V3",
                base_url="https://api.siliconflow.cn/v1",
                api_key=siliconflow_api_key,
                model_info={
                    "family": "deepseek",
                    "context_length": 8192,
                    "max_output_tokens": 2048,
                    "tool_choice_supported": True,
                    "tool_choice_required": False,
                    "structured_output": True,
                    "vision": False,
                    "function_calling": True,
                    "json_output": True
                },
            ),
            "pro-deepseek-v3": OpenAIChatCompletionClient(
                model="Pro/deepseek-ai/DeepSeek-V3",
                base_url="https://api.siliconflow.cn/v1",
                api_key=siliconflow_api_key,
                model_info={
                    "family": "deepseek",
                    "context_length": 8192,
                    "max_output_tokens": 2048,
                    "tool_choice_supported": True,
                    "tool_choice_required": False,
                    "structured_output": True,
                    "vision": False,
                    "function_calling": True,
                    "json_output": True
                },
            ),
            "deepseek-r1": OpenAIChatCompletionClient(
                model="deepseek-ai/DeepSeek-R1",
                base_url="https://api.siliconflow.cn/v1",
                api_key=siliconflow_api_key,
                model_info={
                    "family": "deepseek",
                    "context_length": 8192,
                    "max_output_tokens": 2048,
                    "tool_choice_supported": True,
                    "tool_choice_required": False,
                    "structured_output": True,
                    "vision": False,
                    "function_calling": True,
                    "json_output": True
                },
            ),
            "qwen3": OpenAIChatCompletionClient(
                model="Qwen/Qwen3-30B-A3B",
                base_url="https://api.siliconflow.cn/v1",
                api_key=siliconflow_api_key,
                model_info={
                    "family": "glm",
                    "context_length": 8192,
                    "max_output_tokens": 2048,
                    "tool_choice_supported": True,
                    "tool_choice_required": False,
                    "structured_output": True,
                    "vision": False,
                    "function_calling": True,
                    "json_output": True
                },
            ),
            "glm4": OpenAIChatCompletionClient(
                model="THUDM/GLM-4-32B-0414",
                base_url="https://api.siliconflow.cn/v1",
                api_key=siliconflow_api_key,
                model_info={
                    "family": "glm",
                    "context_length": 8192,
                    "max_output_tokens": 2048,
                    "tool_choice_supported": True,
                    "tool_choice_required": False,
                    "structured_output": True,
                    "vision": False,
                    "function_calling": True,
                    "json_output": True
                },
            ),
            "gpt4o": OpenAIChatCompletionClient(
                model="openai/chatgpt-4o-latest",
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key,
                model_info={
                    "family": "glm",
                    "context_length": 8192,
                    "max_output_tokens": 2048,
                    "tool_choice_supported": True,
                    "tool_choice_required": False,
                    "structured_output": True,
                    "vision": False,
                    "function_calling": True,
                    "json_output": True
                },
            ),
            "gpt4o-mini": OpenAIChatCompletionClient(
                model="openai/gpt-4o-mini",
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key,
                model_info={
                    "family": "glm",
                    "context_length": 8192,
                    "max_output_tokens": 2048,
                    "tool_choice_supported": True,
                    "tool_choice_required": False,
                    "structured_output": True,
                    "vision": False,
                    "function_calling": True,
                    "json_output": True
                },
            ),
            "llama4-maverick": OpenAIChatCompletionClient(
                model="meta-llama/llama-4-maverick",
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key,
                model_info={
                    "family": "glm",
                    "context_length": 8192,
                    "max_output_tokens": 2048,
                    "tool_choice_supported": True,
                    "tool_choice_required": False,
                    "structured_output": True,
                    "vision": False,
                    "function_calling": True,
                    "json_output": True
                },
            ),
            "llama4-scout": OpenAIChatCompletionClient(
                model="meta-llama/llama-4-scout",
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key,
                model_info={
                    "family": "glm",
                    "context_length": 8192,
                    "max_output_tokens": 2048,
                    "tool_choice_supported": True,
                    "tool_choice_required": False,
                    "structured_output": True,
                    "vision": False,
                    "function_calling": True,
                    "json_output": True
                },
            )
        }

    def get_client(self, model_name: str):
        """
        根据模型名称获取对应的 LLM 客户端实例。
        支持 'deepseek-v3'、'deepseek-r1','qwen3'、'glm4'。
        """
        client = self.clients.get(model_name.lower())
        if not client:
            raise ValueError(f"不支持的模型名称: {model_name}")
        return client

# 测试代码
# async def main():
#     llm_manager = LLMClientManager()
#     client = llm_manager.get_client("deepseek-v3")
#     result = await client.create([
#         UserMessage(content="请介绍一下AutoGen框架。", source="user")
#     ])
#     print(result)
#     await client.close()

# if __name__ == "__main__":
#     asyncio.run(main())