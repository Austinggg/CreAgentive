import logger
from Agent.InitializeAgent import create_agents
import os
import json
import asyncio
from Agent.MemoryAgent import MemoryAgent
from Resource.tools.customJSONEncoder import CustomJSONEncoder
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from Agent.StoryGenAgent import create_agents
from Resource.tools.extract_last_content import extract_last_text_content
from Resource.tools.read_json import read_json, read_max_index_file
from Resource.tools.decision import score_plan,evaluate_plan
from Resource.template.story_template import story_plan_template, story_plan_example
from Resource.tools.extract_last_content import extract_last_text_content
from Resource.tools.extract_llm_content import extract_llm_content
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock
from Resource.tools.to_valid_identifier import to_valid_identifier

import logging
from pathlib import Path


class StoryGenWorkflow:
    def __init__(self, model_client, maxround=5):
        self.model_client = model_client
        self.maxround = maxround
        # 初始化知识图谱连接
        self.memory_agent = MemoryAgent()
        self.current_chapter = 0  # 添加章节计数器
        self.initial_data = self._load_initial_data()
        self.env_info = self.initial_data.get("background", {})

    def _load_initial_data(self, file_path="Resource/memory/story_plan/chapter_0.json"):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"初始数据文件不存在: {file_path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logging.error(f"初始数据文件格式错误: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"加载初始数据失败: {str(e)}")
            raise

        required_fields = ["title", "background", "longgoal", "characters", "relationships"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"初始数据缺少必要字段: {', '.join(missing_fields)}")

        return data

    def _get_next_chapter_number(self):
        self.current_chapter += 1
        return self.current_chapter

    def _create_agents(self):
        """创建所有智能体"""
        agents = create_agents(self.model_client)
        self.shortgoal_agent = agents["shortgoalAgent"]
        self.longgoal_agent = agents["longgoalAgent"]

    def _get_role_identity(self, agent_config):
        """
        获取角色基本信息（结构化格式）
        返回格式：
        {
            "properties": {
                "id": str,
                "name": str,
                "age": int,
                "gender": str,
                "affiliations": List[str],
                "occupation": List[str],
                "aliases": List[str]
            },
            "error": Optional[str]
        }
        """
        role_id = agent_config.get("id")
        if not role_id:
            return {"properties": {}, "error": "角色配置缺少ID"}

        try:
            # 使用 MemoryAgent 获取角色信息
            memory = self.memory_agent.get_character_memory(role_id, self.current_chapter - 1)

            if "error" in memory:
                return {"properties": {}, "error": memory["error"]}

            # 结构化返回（包含默认值处理）
            return {
                "properties": {
                    "id": memory["properties"].get("id", role_id),
                    "name": memory["properties"].get("name", "未知角色"),
                    "age": memory["properties"].get("age", 0),
                    "gender": memory["properties"].get("gender", "UNKNOWN"),
                    "affiliations": memory["properties"].get("affiliations", []),
                    "occupation": memory["properties"].get("occupation", []),
                    "aliases": memory["properties"].get("aliases", []),
                    "health_status": memory["properties"].get("health_status", "UNKNOWN"),
                    "personality": memory["properties"].get("personality", "UNKNOWN")
                }
            }

        except Exception as e:
            logging.error(f"获取角色基本信息失败 - 角色ID: {role_id}, 错误: {str(e)}", exc_info=True)
            return {"properties": {}, "error": f"基本信息获取失败: {str(e)}"}

    def _get_role_relation(self, agent_config):
        """
        获取角色在上一章节的关系网络（结构化格式）
        返回格式：
        {
            "relationships": [
                {
                    "character_id": str,
                    "name": str,
                    "type": str,
                    "chapter": int,
                    "intensity": int,
                    "awareness": str
                },
                ...
            ],
            "error": Optional[str]
        }
        """
        role_id = agent_config.get("id")
        if not role_id:
            return {"relationships": [], "error": "角色配置缺少ID"}

        try:
            memory = self.memory_agent.get_character_memory(role_id, self.current_chapter - 1)

            if "error" in memory:
                return {"relationships": [], "error": memory["error"]}

            # 正确处理关系数据结构
            relationships = memory.get("relationships", [])
            return {
                "relationships": [
                    {
                        "person_id": rel.get("character_id", "<UNK>"),
                        "name": rel.get("name", "<UNK>"),
                        "type": rel.get("type", "<UNK>"),
                        "chapter": self.current_chapter - 1,
                        "intensity": rel.get("intensity", 0),
                    }
                    for rel in relationships
                ]
            }

        except Exception as e:
            logging.error(f"获取角色关系失败 - 角色ID: {role_id}, 错误: {str(e)}", exc_info=True)
            return {"relationships": [], "error": f"关系获取失败: {str(e)}"}

    def _get_role_events(self, agent_config):
        """
        获取角色在上一章节参与的事件（结构化格式）
        返回格式：
        {
            "events": [
                {
                    "name": str,
                    "details": str,
                    "scene": str,
                    "emotional_impact": str,
                    "consequences": List[str]
                },
                ...
            ],
            "error": Optional[str]
        }
        """
        role_id = agent_config.get("id")
        if not role_id:
            return {"events": [], "error": "角色配置缺少ID"}

        try:
            memory = self.memory_agent.get_character_memory(role_id, self.current_chapter - 1)

            if "error" in memory:
                return {"events": [], "error": memory["error"]}

            # 正确处理事件数据结构
            return {
                "events": memory["events"]  # 直接返回整个events列表
            }

            # return {
            #     "events": [
            #         {
            #             "name": event.get("name", "<UNK>"),
            #             "details": event.get("details", ""),
            #             "scene": event.get("scene", "未知场景"),
            #             "emotional_impact": event.get("emotional_impact", "无记录"),
            #             "consequences": event.get("consequences", [])
            #         }
            #         for event in events
            #     ]
            # }

        except Exception as e:
            logging.error(f"获取角色事件失败 - 角色ID: {role_id}, 错误: {str(e)}", exc_info=True)
            return {"events": [], "error": f"事件获取失败: {str(e)}"}


    def _create_role_prompt(self, role_relation, role_events, role_identity):
        """创建角色智能体的系统提示词"""
        # 将模板和示例转换为格式化的JSON字符串
        template_str = json.dumps(story_plan_template, ensure_ascii=False, indent=2)
        example_str = json.dumps(story_plan_example, ensure_ascii=False, indent=2)

        role_prompt = (
            "# 角色行为规划师指令\n"
            "## 基本信息\n"
            f"身份: {role_identity}\n"
            f"关系网: {role_relation}\n"
            f"历史事件: {role_events}\n\n"
            "## 任务要求\n"
            "1. 根据以上信息生成符合角色特征的接下来一章节方案\n"
            "2. 保持角色性格和行为一致性\n"
            "3. 方案需基于当前环境信息和短期目标\n"
            "4. 方案可以考虑将人物关系进行适当变化\n"
            "5. 每次生成均是对上一方案进行优化迭代\n\n"
            "## 输出格式\n"
            "### 模板结构:\n"
            f"{template_str}\n\n"
            "### 示例参考:\n"
            f"{example_str}\n\n"
            "## 注意事项\n"
            "- 输出纯JSON格式，不要包含Markdown或其他格式化标记\n"
            "- 确保所有字段完整且类型正确\n"
            "- 情感状态需符合角色性格\n"
            "- 事件顺序需保持时间线连贯"
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

        goal_data = json.loads(envinfo)

        # 新增调试用
        # 如果 agents_config 里有字符串，就把它当成 id 和 role_name 包装成 dict
        fixed = []
        for raw in agents_config:
            if isinstance(raw, str):
                fixed.append({"id": raw, "role_name": raw})
            else:
                fixed.append(raw)
        agents_config = fixed
        # —— 到此结束 —— 

        print("envinfo =================================\n")
        print(envinfo)
        print("agents_config ==============================\n")
        print(agents_config)
        print(f"agent_config的类型:{type(agents_config)}")
        print("agents_config ==============================\n")

        
        # 问题在于 提示词中的 .get() , 根本问题在于 ENVINFO 是一个字符串，需要核对传入的 envinfo
        # 1. 创建环境信息Agent (优化后的提示词)
        env_prompt = (
            "## 环境信息管理员\n"
            "你负责维护当前章节的环境上下文，包括但不限于:\n"
            f"- 章节目标: {goal_data.get('chapter_goal', '未设定')}\n"
            f"- 关键任务: {', '.join(goal_data.get('key_tasks', []))}\n"
            f"- 新增冲突: {goal_data.get('new_conflicts', '无')}\n"
            f"- 预期结果: {goal_data.get('expected_outcomes', '未设定')}\n\n"
            "你的职责:\n"
            "1. 当角色偏离主线时提供环境提示\n"
            "2. 解答关于场景规则的询问\n"
            "3. 不主动参与角色决策\n"
            "4. 确保讨论不超出当前章节范围"
        )

        env_agent = AssistantAgent(
            name="Env_Agent",
            description="用于提供环境信息，不作为角色进行对话",
            model_client=self.model_client,
            system_message=env_prompt,
        )
        print(f"{env_agent.name} 创建成功")

        # 2. 动态创建角色 agent
        role_agents = []
        for agent_config in agents_config:
            # 构建每个 角色 agent 的 prompt
            # TODO： 需要根据具体的角色信息文件的格式进行调整
            role_relation = self._get_role_relation(agent_config) # 读取角色在上一章节的关系
            role_events = self._get_role_events(agent_config) # 读取角色在上一章节所发生的事件
            role_identity = self._get_role_identity(agent_config) # 读取角色的基本信息
            role_prompt = self._create_role_prompt(role_relation, role_events, role_identity)
            # 角色名称读取
            # role_name = agent_config.get("name", agent_config.get("id", "Unknown"))
            # 简单的名称处理
            # role_name = agent_config.get("id", f"role_{len(role_agents)}")
            # # 确保名称中没有空格等无效字符
            # role_name = role_name.replace(" ", "_").replace("-", "_")
            # 获取显示用的名字（中文）
            display_name = agent_config.get("name", "未知角色")

            # 获取合法的 agent name（用于内部逻辑）
            agent_id = agent_config.get("id", f"role_{len(role_agents)}")
            role_name = to_valid_identifier(agent_id)

            print(f"当前角色名称{role_name}")

            agent = AssistantAgent(
                name=role_name, # 要修改name读取逻辑
                model_client=self.model_client,
                system_message=role_prompt
            )
            role_agents.append(agent)

        # 3. 构建多智能体对话 team
        chat_team = RoundRobinGroupChat(
            participants=[env_agent] + role_agents, # 组合所有将参与对话的 agent 包含 环境智能体 + 角色智能体
            # max_turns=self.maxround,# 循环最大轮数
            max_turns=self.maxround
        )

        # 返回 智能体对话集群
        return chat_team

    def _save_chapter(self, plan):
        """
        将生成的 plan 保存为 JSON 文件，文件名格式为 chapterN.json，
        N 为当前文件夹中最大编号 + 1。

        参数:
            plan (dict): 要保存的 plan 数据，应为字典格式。
        """

        plan["chapter"] = self.current_chapter  # 直接使用当前章节号
        # Plan 保存路径
        folder_path = Path("Resource/memory/story_plan")
        folder_path.mkdir(parents=True, exist_ok=True)

        # 获取当前最大编号文件
        try:
            latest_plan = read_max_index_file(str(folder_path))
            current_max_chapter = latest_plan.get("chapter", 0) if isinstance(latest_plan, dict) else 0
        except Exception as e:
            logging.warning(f"获取最大章节号失败，将从头开始: {str(e)}")
            current_max_chapter = 0

        # 新章节编号 = 最大编号 + 1
        new_chapter_num = current_max_chapter + 1
        new_file_name = f"chapter_{new_chapter_num}.json"
        new_file_path = folder_path / new_file_name

        try:
            # 将 plan 写入文件
            with open(new_file_path, 'w', encoding='utf-8') as f:
                json.dump(plan, f, ensure_ascii=False, indent=4, cls=CustomJSONEncoder)

            logging.info(f"新章节已保存为: {new_file_path}")

            # 更新知识图谱
            self.memory_agent.build_graph_from_json(str(new_file_path))
            logging.info(f"知识图谱已更新")

            # 保存角色记忆
            self.memory_agent.save_character_memories(new_chapter_num)
            logging.info(f"角色记忆已保存")

        except Exception as e:
            logging.error(f"保存章节失败: {str(e)}", exc_info=True)
            raise

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

    async def _if_get_longgoal(self, long_goal, plan):
        """
        判断是否实现了长期目标
        """
        # TODO: 需要完善 LonggoalAgent 的提示词
        # 判断当前方案是否实现长期目标
        
        # .run 需要加入参数，调通阶段，暂时不加参数
        response = await self.longgoal_agent.run()
        result = response if isinstance(response, str) else str(response)

        # 判断是否实现长期目标，实现则返回 True，否则返回 False
        if result == "YES":
            return True
        else:
            return False

    async def run(self):
        """
        运行故事生成智能体工作流的主入口
        流程：
        1. 初始化智能体和数据
        2. 循环生成每个章节的内容
        3. 每章生成三轮不同方案并进行评分
        4. 检查是否达成长期目标，决定是否终止流程
        """
        # === 1. 初始化阶段 ===
        print("🚀 初始化智能体...")
        self._create_agents()  # 创建短期目标和长期目标智能体

        try:
            # 加载初始数据
            initial_data = self._load_initial_data()
            long_goal = initial_data["longgoal"]  # 获取长期目标
            initial_characters = initial_data["characters"]  # 初始角色配置
            initial_env_info = initial_data["background"]  # 初始环境设置

            # 打印检查是否正常读取初始数据
            print(f"初始长期目标: {long_goal}")
            print(f"初始角色配置: {initial_characters}")
            print(f"初始环境设置: {initial_env_info}")

            # 验证必要数据是否存在
            if not all([long_goal, initial_characters, initial_env_info]):
                raise ValueError("初始数据缺少必要字段")

        except Exception as e:
            print(f"⚠️ 初始化失败: {str(e)}")
            return
        
        print("初始化完毕\n")

        # === 2. 章节生成主循环 ===
        while True:
            chapter_num = self._get_next_chapter_number()
            print(f"\n📖 开始生成第 {chapter_num} 章...")

            # -- 2.1 准备当前章节数据 --
            try:
                # 尝试读取上一章内容（首次运行时编号为  -1 ）
                last_chapter_plan, chapter_number  = read_max_index_file("Resource/memory/story_plan")
                print(f"上一章序号：{chapter_number}")
                print("上一章内容：\n" + str(last_chapter_plan))

                # 如果是第一章，使用初始配置；否则使用上一章配置
                if chapter_number == 0:
                    print("使用初始角色和环境配置")
                    current_env = initial_env_info
                    agents_config = initial_characters
                else:
                    current_env, agents_config = self._read_info_from_plan(last_chapter_plan)

            except Exception as e:
                print(f"⚠️ 加载历史数据失败: {str(e)}")
                current_env = initial_env_info  # 失败时回退到初始配置
                agents_config = initial_characters

            # -- 2.2 生成短期目标 --
            try:
                # 构造短期目标生成提示（包含长期目标和当前环境）
                prompt = (
                    f"长期目标: {long_goal}\n"
                    f"当前环境: {json.dumps(current_env, ensure_ascii=False)}\n"
                    f"请生成第 {chapter_num} 章的短期目标"
                )

                print(f"短期目标生成提示：\n{prompt}")

                # 调用短期目标智能体（直接await异步调用）
                short_goal = await self.shortgoal_agent.run(task=prompt)

                # 打印短期目标
                print(f"短期目标：\n{short_goal}")

                # 需从 autogen 的输出中剥离 shortgoal，并且要去掉 Markdown 语法
                short_goal = strip_markdown_codeblock(extract_llm_content(short_goal))
                print(f"短期目标的类型: {type(short_goal)}")
                print(f"短期目标,优化后：\n{short_goal}")


                # 确保返回值为字符串（智能体可能返回不同格式）
                if not isinstance(short_goal, str):
                    short_goal = str(short_goal)
            except Exception as e:
                print(f"⚠️ 生成短期目标失败: {str(e)}")
                continue  # 跳过本章节

            print("\n ====================开始多轮方案生成 ========================  \n")

            # -- 2.3 多轮方案生成 --
            round_plans = []
            for round_num in range(1, 4):  # 生成三轮不同方案
                print(f"  第 {round_num} 轮方案生成中...")

                try:
                    # 创建角色团队（包含环境智能体和所有角色智能体）
                    team = self._create_team_from_config(agents_config, short_goal)

                    # 运行团队讨论（明确指定任务格式）
                    response = await team.run(
                        task=json.dumps({
                            "instruction": "生成完整故事方案",
                            "requirements": [
                                "保持角色性格一致性",
                                "推进长期目标发展",
                                f"实现短期目标: {short_goal}"
                            ]
                        })
                    )


                    # 直接保存响应内容（不尝试解析）
                    final_content = str(response)
                    round_plans.append(final_content)
                    print(f"  第 {round_num} 轮方案已保存")

                except Exception as e:
                    print(f"⚠️ 第 {round_num} 轮生成失败: {str(e)}")
                    continue

            # -- 2.4 方案评估与保存 --
            if not round_plans:
                print("⚠️ 未生成任何有效方案，跳过本章节")
                continue

            print("🚀 开始评估方案")
            # print(round_plans)
            # print(type(round_plans))

            try:
                # 评分并选择最佳方案
                print(f"🚀 评估中...")
                best_plan, best_score = await evaluate_plan(round_plans, self.model_client)

                print(f"✅ 最佳方案评分: {best_score}")
                print(f"✅ 最佳方案: {best_plan}")

                # 保存章节数据
                self._save_chapter({
                    "chapter": chapter_num,
                    "content": best_plan,
                    "env": current_env,
                    "agents_config": agents_config
                })

                # 更新知识图谱,
                # TODO: 这个地方要修改成路径
                # self.memory_agent.build_graph_from_json(best_plan)
            except Exception as e:
                print(f"⚠️ 方案保存失败: {str(e)}")
                continue

            # -- 2.5 长期目标检查 --
            try:
                if await self._if_get_longgoal(long_goal, best_plan):
                    print("🎉 故事已达成长期目标，生成完成！")
                    break
            except Exception as e:
                print(f"⚠️ 长期目标检查失败: {str(e)}")
                continue  # 继续生成下一章

        # === 3. 收尾工作 ===
        print("🏁 故事生成流程结束")