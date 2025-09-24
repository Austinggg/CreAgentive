import asyncio
from Resource.llmclient import LLMClientManager
from collections import deque # 用于测试输入队列
from Workflow.Accessment_wk import AccessmentWorkflow
# 导入英文版的测试代码
from Workflow.Wok_Eng.Init_wk import InitialWorkflow
from Workflow.Wok_Eng.Writing_wk import WritingWorkflow
from Workflow.Wok_Eng.StoryGen_wk import StoryGenWorkflow
# 初始化模型客户端
model_client = LLMClientManager().get_client("deepseek-v3")

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
initialworkflow = InitialWorkflow(model_client, test_inputs_Eng)  # The Initialization Workflow
storygenworkflow = StoryGenWorkflow(model_client)  # The Story Generation Workflow
writingworkflow = WritingWorkflow(model_client)  # The Writing Workflow
# accessmentworkflow = AccessmentWorkflow(model_client)


async def main():
    # init_result = await initialworkflow.run()
    await storygenworkflow.run()
    await writingworkflow.run()


if __name__ == "__main__":
    asyncio.run(main())


