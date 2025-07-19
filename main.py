from Workflow.Init_wk import InitialWorkflow
from Workflow.Writing_wk import WritingWorkflow
from Workflow.StoryGen_wk import StoryGenWorkflow
from Resource.llmclient import LLMClientManager
from collections import deque # 用于测试输入队列

# 初始化模型客户端
model_client = LLMClientManager().get_client("deepseek-r1")

# 测试输入队列
test_inputs = deque([
    "我想要一个悬疑的故事，里面要3个主人公，荒岛求生的类型。",
    "故事的背景设定在一个神秘的荒岛上，主人公们需要面对未知的挑战和危险。",
    "希望故事风格轻松幽默，语言风格简洁明了。",
    "主人公分别是一个机智的侦探，一个勇敢的探险家，还有一个善于解谜的科学家。",
    "故事中要包含不少紧张刺激的追逐场面和意想不到的反转。",
    "请在情节设计中加入一些心理描写，展现角色内心的矛盾和成长。",
    "结局希望是开放式的，留给读者一定的想象空间。",
    "请控制故事长度在3000字以内，适合短篇小说阅读。",
])

# 创建工作流实例
initialworkflow = InitialWorkflow(model_client, test_inputs) # 初始化工作流
storygenworkflow = StoryGenWorkflow(model_client) # 故事生成工作流
writingworkflow = WritingWorkflow(model_client) # 写作工作流


# ============================================================================
# ================================= 运行工作流 ================================
# ============================================================================

# 运行初始化工作流
# init_result = initialworkflow.run()

# 运行故事生成工作流
#storygenworkflow.run(init_result)

# 运行写作工作流
writingworkflow.run()