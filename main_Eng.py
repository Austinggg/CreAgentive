import asyncio
# from Workflow.Init_wk import InitialWorkflow
# from Workflow.Writing_wk import WritingWorkflow
# from Workflow.StoryGen_wk import StoryGenWorkflow
from Resource.llmclient import LLMClientManager
from collections import deque # 用于测试输入队列
from Workflow.Accessment_wk import AccessmentWorkflow
# 导入英文版的测试代码
from Workflow.Wok_Eng.Init_wk import InitialWorkflow
from Workflow.Wok_Eng.Writing_wk import WritingWorkflow
from Workflow.Wok_Eng.StoryGen_wk import StoryGenWorkflow
# 初始化模型客户端
model_client = LLMClientManager().get_client("deepseek-v3")

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
test_inputs_Eng = deque([
    "I want a suspenseful story featuring three main characters, centered around survival on a deserted island.",
    "The story should be set on a mysterious island, where the protagonists face unknown challenges and dangers.",
    "I'd like the tone to be light and humorous, with a clear and concise writing style.",
    "The main characters should be: a clever detective, a brave explorer, and a puzzle-solving scientist.",
    "The plot should include several intense chase scenes and unexpected plot twists.",
    "Please incorporate psychological insights to reveal the characters’ inner conflicts and personal growth.",
    "I prefer an open-ended conclusion that leaves room for the reader’s imagination.",
    "Please keep the story under 3,000 words, suitable for a short story format",
])

# 创建工作流实例
initialworkflow = InitialWorkflow(model_client, test_inputs_Eng)  # 初始化工作流
storygenworkflow = StoryGenWorkflow(model_client)  # 故事生成工作流
writingworkflow = WritingWorkflow(model_client)  # 写作工作流
# accessmentworkflow = AccessmentWorkflow(model_client)

# ============================================================================
# ================================= 运行工作流 ================================
# ============================================================================

async def main():
    # print("开始初始化")
    # 运行初始化工作流
    # init_result = await initialworkflow.run()
    # # 运行故事生成工作流
    await storygenworkflow.run()

    # 运行写作工作流
    # await writingworkflow.run()

    # await accessmentworkflow.run()


if __name__ == "__main__":
    asyncio.run(main())


