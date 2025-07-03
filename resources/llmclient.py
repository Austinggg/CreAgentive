import os
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient

# 加载环境变量
load_dotenv()
# 获取硅基流动平台的 API 密钥
siliconflow_api_key = os.getenv("SILICONFLOW_API_KEY")
# print("读取到的 API Key 是：", siliconflow_api_key)

# 初始化 DeepSeek-V3 模型客户端
Deepseek_client = OpenAIChatCompletionClient(
    model="deepseek-ai/DeepSeek-V3",                # 模型名称
    base_url="https://api.siliconflow.cn/v1",       # API 地址
    api_key=siliconflow_api_key,                    # API 密钥
    model_info={
        "family": "qwen",              
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

# 初始化 Qwen3-30B 模型客户端
QWEN_client = OpenAIChatCompletionClient(
    model="Qwen/Qwen3-30B-A3B",                     # 模型名称
    base_url="https://api.siliconflow.cn/v1",       # API 地址
    api_key=siliconflow_api_key,                    # API 密钥
    model_info={
        "family": "qwen",              
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

# 初始化 GLM4-32B 模型客户端
GLM_client = OpenAIChatCompletionClient(
    model="THUDM/GLM-4-32B-0414",                   # 模型名称
    base_url="https://api.siliconflow.cn/v1",       # API 地址
    api_key=siliconflow_api_key,                    # API 密钥
    model_info={
        "family": "qwen",              
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

# print("硅基流动平台的模型客户端已成功初始化！")