from Agent.InitializeAgent import create_agents
import os
import json
from Resource.tools.customJSONEncoder import CustomJSONEncoder
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat  # 引入轮询式群聊团队类
from Agent.StoryGenAgent import create_agents
from Resource.template.storygen_prompt.longgoal import longgoal_prompt_template
from Resource.tools.extract_last_content import extract_last_text_content
from Resource.tools.read_json import read_json, read_max_index_file


class StoryGenWorkflow:
    def __init__(self, model_client, maxround=5):
        self.model_client = model_client
        self.maxround = maxround

    def _create_agents(self):
        """创建所有智能体"""
        
        agents = create_agents(self.model_client)
        self.shortgoal_agent = agents["shortgoalAgent"]
        self.longgoal_agent = agents["longgoalAgent"]
    

    # TODO: 修改该函数， 实现对角色信息的检索
    def _get_role_relation(self):
        """
        获取角色在上一节的关系网络
        """
        pass

    # TODO: 修改该函数， 实现对角色相关事件的检索
    def _get_role_events(self):
        """
        获取角色在上一章节所发生的事件
        """
        
        pass
    def _create_role_prompt(self, role_relation, role_events, role_identity):
        """创建角色智能体的系统提示词"""
        # Todo： 这部分的提示词需要优化,要规范输出的方案格式，太长的话 可以存储成 template
        role_prompt = (
            "# 基本设定：你现在的基本信息如下所示：\n"
            f"你的身份信息为： {role_identity}\n"
            f"你的人际关系为：{role_relation}\n"
            f"你曾经参与过的事件包含：{role_events}\n"
            "请根据你的身份、背景关系和经历的事件，保持角色性格和行为一致性。\n"
            "过程中，你不是进行对话，你是根据当前场景的环境信息和短期目标，产出你认为你最佳的行动方案。\n"
            "并且你基于你上一个的方案来进行优化方案。\n"
            "你产生的行动方案的格式如下："
            "格式"
            "注意：输出的方案不要带有 markdown 格式或其他格式化标记。"
        )
        return role_prompt
    def _create_team_from_config(self,agents_config: list, envinfo):
        """
        根据配置创建 Agent 团队并构建协作流程。

        参数:
            agents_config (list): 从配置文件加载的 Agent 配置列表。
            llm_config (dict): 团队管理者的 LLM 配置。
            max_round (int): 最大对话轮次。
            speaker_selection_method (str): 发言人选择方式。

        返回:
            tuple: (user_proxy, group_chat_manager) 可用于启动对话。
        """

        # 1. 创建知晓 环境信息的 agent
        env_agent = AssistantAgent(
            name="Env Agent",
            description="用于提供环境信息，不作为角色进行对话",
            client = self.model_client,
            system_message= f"{envinfo}\n，以上为当前章节对话信息，包含短期目标等" # Todo： 这个提示词待优化
        )

        # 2. 动态创建角色 agent
        # Todo: 需要给 Agent 读取他 上一章节的 记忆 的功能，抓取人物关系
        role_agents = []
        for agent_config in agents_config:
            # 构建每个 角色 agent 的 prompt
            # TODO： 需要根据具体的角色信息文件的格式进行调整
            role_relation = self._get_role_relation(agent_config) # 读取角色在上一章节的关系
            role_events = self._get_role_events(agent_config) # 读取角色在上一章节所发生的事件
            role_indentity = agent_config.get("system_message", "") # 读取角色的基本信息
            role_prompt = self._create_role_prompt(role_relation, role_events, role_indentity)

            agent = AssistantAgent(
                name=agent_config["role_name"],
                client=self.model_client,
                system_message=role_prompt
            )
            role_agents.append(agent)

        # 3. 构建多智能体对话 team
        chat_team = RoundRobinGroupChat(
            agents=[env_agent] + role_agents, # 组合所有将参与对话的 agent 包含 环境智能体 + 角色智能体
            max_round=self.maxround, # 循环最大轮数
        )

        # 返回 智能体对话集群
        return chat_team
    
    # TODO: 评分函数待完善，DNF 需要训练模型
    def _score_plan(self, plans:list):
        """
        对传入的 plan 列表中的每个元素进行评分，选出得分最高的 plan 并返回。

        参数:
            plans (list): 包含多个方案的列表，每个方案是一个字符串或字典。

        返回:
            any: 评分最高的 plan。
        """

        if not plans:
            print("没有可供选择的方案。传入为空")
            return None

        # 使用内置函数对每个 plan 进行评分，
        # Todo: 修改成基于 Agent 的决策评分方法（模型需要训练）
        scored_plans = [(plan, self._evaluate_plan(plan)) for plan in plans]

        # 找出评分最高的 plan
        best_plan, best_score = max(scored_plans, key=lambda x: x[1])

        print(f"最佳方案得分: {best_score}")
        return best_plan


    def _save_chapter(self, plan):
        """
        将生成的 plan 保存为 JSON 文件，文件名格式为 chapterN.json，
        N 为当前文件夹中最大编号 + 1。
    
        参数:
            plan (dict): 要保存的 plan 数据，应为字典格式。
        """

        # Plan 保存路径
        folder_path = r"Resource/memory/story_plan"

        # 获取当前最大编号文件
        try:
            latest_plan = read_max_index_file(folder_path)
            # 提取文件名中的编号
            if isinstance(latest_plan, str):
                with open(latest_plan, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
            elif isinstance(latest_plan, dict):
                plan_data = latest_plan
            else:
                raise ValueError("latest_plan 必须是文件路径或字典")

            current_max_chapter = plan_data.get("chapter", 0)
        except Exception as e:
            current_max_chapter = 0

        # 新章节编号 = 最大编号 + 1
        new_chapter_num = current_max_chapter + 1
        new_file_name = f"chapter{new_chapter_num}.json"
        new_file_path = os.path.join(folder_path, new_file_name)

        # 将 plan 写入文件
        with open(new_file_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=4)

        print(f"新章节已保存为: {new_file_path}")



    def _read_info_from_plan(self, plan):
        """
        从 plan JSON 文件中读取 env 和 agents_config 信息。

        参数:
            plan (str or dict): 如果是字符串，表示 JSON 文件路径；如果是字典，表示已加载的 JSON 内容。

        返回:
            tuple: (env_info, agents_config)
        """
        # Todo: 需要根据实际的方案 json 格式 修改读取内容
        if isinstance(plan, str):
            # 如果 plan 是文件路径，则读取 JSON 文件
            with open(plan, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)
        elif isinstance(plan, dict):
            # 如果 plan 已是解析后的字典，直接使用
            plan_data = plan
        else:
            raise ValueError("plan 参数必须是文件路径字符串或已解析的字典。")

        # 提取 env 和 agents_config
        env_info = plan_data.get("env", {})
        agents_config = plan_data.get("agents_config", [])

        return env_info, agents_config

    def _get_longgoal(self):
        """
        读取初始化方案 json 文件中的长期目标，获取 longgoal 字段内容。
        初始化方案为 chapter0.json。
        
        :return: str, 长期目标内容。
        """
        # 定义json文件的路径
        file_path = r'Resource/memory/story_plan/chapter0.json'

        try:
            # 打开并读取json文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 获取longgoal字段内容   
            long_goal = data.get("longgoal", "")
            # 如果longgoal字段内容为空，则抛出异常
            if not long_goal:
                raise ValueError("JSON 文件中不存在 'longgoal' 字段或其值为空。")
            # 返回longgoal字段内容
            return long_goal
        except Exception as e:
            # 捕获异常并打印错误信息
            print(f"读取 longgoal 时发生错误: {e}")
            # 发生异常时返回空字符串
            return ""

    def _if_get_longgoal(self, long_goal, plan):
        """
        判断是否实现了长期目标
        """
        # TODO: 需要完善 LonggoalAgent 的提示词
        # 判断当前方案是否实现长期目标
        result = extract_last_text_content(self.longgoal_agent.run(plan))

        # 判断是否实现长期目标，实现则返回 True，否则返回 False
        if result == "YES":
            return True
        else:
            return False

    def run(self):
        """
        运行故事生成智能体工作流
        """

        print(f"🚀 创建智能体...")
        self._create_agents()

        print(f"🚀 运行故事生成智能体工作流...")
        # 读取初始化方案中的 长期目标
        long_goal = self._get_longgoal()

        # 多智能体 逐章生成故事情节
        while True:

            # 定义一个列表存储三轮出现的方案
            # 定义存储三轮方案的列表
            round_plans = []

            # 读取上一章节的方案（初始章节算 第 0 章，也是上一章节）
            # Todo : 1.读取方案的格式问题; 2. 规范 stroy_plan 的文件命名格式。
            last_chapter_plan = read_max_index_file() # 自动读取最新的方案（上一节的方案）
            env_info, agents_config = self._read_info_from_plan(last_chapter_plan) # 读取方案中的 其他环境等信息，此时不包含短期目标，只包含长期目标和环境基本信息; 读取方案中的角色配置信息

            # 开始循环, 生成三个不同的短期目标，即循环三轮
            for round_num in range(1,4): # 循环三次，表示

                # 创建短期目标智能体, 用于生成当前章节短期目标
                # TODO: 生成短期目标，这个提示词要优化
                chapter_plan_init = extract_last_text_content(self.shortgoal_agent.run(task=env_info))

                # 根据初始化信息创建角色智能体 对话集群 team
                role_chat_team =  self._create_team_from_config(agents_config, chapter_plan_init)

                # 根据短期目标进行多智能体讨论 讨论过程为 广播形式
                # TODO：提示词待优化
                response = role_chat_team.run(task="请根据 短期目标，生成一个完整的故事方案，并返回结果。")

                # 4. 提取最终方案并添加到列表，提取了team 输出的最后一个 content
                final_content = extract_last_text_content(response)
                round_plans.append(final_content)

                print(f"第 {round_num} 轮讨论结果已保存")

            # 对生成的方案进行评分，并选出最佳方案,
            # Todo: 评分决策系统还未实现
            # best_plan = self._score_plan(round_plans)
            # 暂时选择第一个方案使用
            best_plan = round_plans[0]
            # Todo: 更新memory 模块还未实现，需要保存至 neo4j 中
            # self._save_chapter(best_plan)
            self._save_chapter(best_plan)

            # 判断是否实现 长期目标，若实现则退出循环
            if self._if_get_longgoal(long_goal, best_plan):
                break

