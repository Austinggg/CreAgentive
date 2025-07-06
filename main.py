from workflow.Init_wk import InitialWorkflow
from resource.llmclient import LLMClientManager
from collections import deque

# 初始化模型客户端
model_client = LLMClientManager().get_client("deepseek-v3")

# 测试输入队列
test_inputs = deque([
    "我想要一个悬疑的故事，里面要3个主人公，荒岛求生的类型" +
    "故事的背景设定在一个神秘的荒岛上，主人公们需要面对未知的挑战和危险。" +
    "希望故事风格轻松幽默，语言风格简洁明了。"
])

# 创建工作流实例
workflow = InitialWorkflow(model_client, test_inputs)

# 启动工作流
result = workflow.run()