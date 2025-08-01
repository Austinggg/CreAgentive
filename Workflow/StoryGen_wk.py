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
    def __init__(self, model_client, maxround=3):
        # 设置模型客户端和最大轮次参数
        self.model_client = model_client  #设置模型客户端
        self.maxround = int(maxround)  #设置模型最大轮次参数, 所有角色智能体参与一次对话为一轮
        self.memory_agent = MemoryAgent()  # 初始化知识图谱连接
        self.current_chapter = 0  # 添加章节计数器(从0开始)

        # 加载初始数据（直接使用原始chapter_0.json）
        init_file = "Resource/memory/story_plan/chapter_0.json"
        self.initial_data = self._load_initial_data(init_file)

        # 静态数据存储
        self.title = self.initial_data["title"]
        self.background = self.initial_data["background"]
        self.longgoal = self.initial_data["longgoal"]
        self.agents_config = self.initial_data["characters"]  # 初始角色配置

        # 直接调用MemoryAgent加载初始化人物和关系，保存至知识图谱
        self.memory_agent.load_initial_data(init_file)


        # 存储上一章节的方案
        self.last_plan = None

        logging.info(
            f"初始化完成 - 标题: {self.title}, "
            f"角色数: {len(self.initial_data['characters'])}, "
            f"关系数: {len(self.initial_data['relationships'])}"
        )

    def _load_initial_data(self, file_path: str) -> dict:
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
            "character": {  # 角色完整数据（与MemoryAgent原始结构一致）
                "id": str,               # 角色ID
                "name": str,             # 姓名
                "age": int,             # 年龄
                "gender": str,           # 性别（MALE/FEMALE/UNKNOWN）
                "affiliations": List[str], # 所属组织
                "occupation": List[str], # 职业
                "aliases": List[str],    # 别名
                "health_status": str,    # 健康状况
                "personality": str,      # 性格描述
            },
            "error": Optional[str]       # 错误信息（失败时存在）
        }
        """
        role_id = agent_config.get("id")
        if not role_id:
            return {"error": "角色配置缺少ID"}

        try:
            memory = self.memory_agent.get_character_memory(role_id, max(0,self.current_chapter - 1))
            return {"characters": memory["characters"]}  # 直接返回完整人物信息
        except Exception as e:
            logging.error(f"获取角色信息失败: {str(e)}")
            return {"error": str(e)}

    def _get_role_relation(self, agent_config):
        """
        获取角色在上一章节的关系网络（结构化格式）
        返回格式：
        {
            "relationships": [  # 关系列表（原始结构）
                {
                    "character_id": str,  # 关联角色ID
                    "name": str,         # 关联角色名称
                    "type": str,         # 关系类型（如'债务关系'）
                    "chapter": int,      # 关系所属章节
                    "intensity": int,    # 关系强度（1-10）
                    "awareness": str,    # 关系认知状态（可选）
                },
                ...
            ],
            "error": Optional[str]      # 错误信息（失败时存在）
        }
        """
        role_id = agent_config.get("id")
        if not role_id:
            return {"error": "角色配置缺少ID"}

        try:
            memory = self.memory_agent.get_character_memory(role_id, max(0,self.current_chapter - 1))
            return {"relationships": memory["relationships"]}  # 直接返回完整关系
        except Exception as e:
            logging.error(f"获取角色关系失败: {str(e)}")
            return {"error": str(e)}

    def _get_role_events(self, agent_config):
        """
        获取角色在上一章节参与的事件（结构化格式）
        返回格式：
        返回格式:
        {
            "events": [  # 事件列表（原始结构）
                {
                    "event_id": str,      # 事件唯一标识
                    "event_name": str,    # 事件名称
                    "event_order": int,    # 事件顺序
                    "details": str,       # 事件详细描述
                    "scene_id": str,      # 所属场景ID
                    "scene_name": str,    # 场景名称
                    "scene_place": str,    # 场景地点
                    "emotional_impact": str, # 情感影响
                    "consequences": List[str], # 后续影响
                },
                ...
            ],
            "error": Optional[str]       # 错误信息（失败时存在）
        }
        """
        print(f"{agent_config}")
        role_id = agent_config.get("id")
        if not role_id:
            return {"events": [], "error": "角色配置缺少ID"}

        try:
            memory = self.memory_agent.get_character_memory(role_id, max(0,self.current_chapter - 1))

            if "error" in memory:
                return {"events": [], "error": memory["error"]}

            # 正确处理事件数据结构
            return {
                "events": memory["events"]  # 直接返回整个events列表
            }

        except Exception as e:
            logging.error(f"获取角色事件失败 - 角色ID: {role_id}, 错误: {str(e)}", exc_info=True)
            return {"events": [], "error": f"事件获取失败: {str(e)}"}


    def _create_role_prompt(self, role_relation, role_events, role_identity, short_goal):
        """创建角色智能体的系统提示词"""
        # 将模板和示例转换为格式化的JSON字符串
        template_str = json.dumps(story_plan_template, ensure_ascii=False, indent=2)
        example_str = json.dumps(story_plan_example, ensure_ascii=False, indent=2)

        role_prompt = (
            "# 你是小说中的一个角色\n"
            "## 角色基本信息\n"
            f"身份: {role_identity}\n"
            f"关系网: {role_relation}\n"
            f"在上一章中所参与的历史事件: {role_events}\n\n"
            "## 任务要求\n"
            "1. 根据以上信息生成符合角色特征的接下来一章节方案\n"
            f"2. 你生成的方案需要依据当前章节的短期目标: {short_goal}\n"
            "3. 方案需要生成5-10个有序事件\n"
            "4. 方案可以考虑将人物关系进行适当变化\n"
            "5. 每次生成均是对上一方案进行优化迭代\n\n"
            "## 输出格式\n"
            "### 模板结构:\n"
            f"{template_str}\n\n"
            "### 示例参考(仅学习其格式，不学习具体内容）:\n"
            f"{example_str}\n\n"
            "### 只需生成以下三个部分：\n"
            "1. relationships: 角色关系变化\n"
            "2. scenes: 新场景(2-3个)\n"
            "3. events: 事件序列(5-10个)\n\n"
            "### 禁止生成\n"
            "- chapter/characters等固定字段\n"
            "## 注意事项\n"
            "- 输出纯JSON格式，不要包含Markdown或```json等其他格式化标记\n"
            "- 确保所有字段完整且类型正确\n"
            "- 情感状态需符合角色性格\n"
            "- 事件顺序需保持时间线连贯"
        )
        return role_prompt

    def _process_llm_output(self, llm_output: str) -> dict:
        """处理LLM输出并拼接固定字段"""
        try:
            dynamic_data = json.loads(strip_markdown_codeblock(llm_output))

            # 验证必须字段
            required_keys = ["relationships", "scenes", "events"]
            if not all(k in dynamic_data for k in required_keys):
                raise ValueError("LLM输出缺少必要字段")

            # 拼接最终数据（固定顺序）
            final_data = {
                "chapter": self.current_chapter,
                "characters": self.initial_data["characters"],
                **dynamic_data  # 剩余字段
            }

            return final_data

        except Exception as e:
            logging.error(f"处理LLM输出失败: {str(e)}")
            raise

    def _create_team_from_config(self, short_goal):
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

        # goal_data = self.longgoal

        # 新增调试用
        # 如果 agents_config 里有字符串，就把它当成 id 和 role_name 包装成 dict
        fixed = []
        for raw in self.agents_config:
            if isinstance(raw, str):
                fixed.append({"id": raw, "role_name": raw})
            else:
                fixed.append(raw)
        agents_config = fixed
        # —— 到此结束 —— 

        # print("envinfo =================================\n")
        print("agents_config ==============================\n")
        print(self.agents_config)
        print(f"agent_config的类型:{type(self.agents_config)}")
        print("agents_config ==============================\n")

        
        # # 问题在于 提示词中的 .get() , 根本问题在于 ENVINFO 是一个字符串，需要核对传入的 envinfo
        # # 1. 创建环境信息Agent (优化后的提示词)
        # env_prompt = (
        #     "## 环境信息管理员\n"
        #     "你负责维护当前章节的环境上下文，包括但不限于:\n"
        #     f"- 章节目标: {goal_data.get('chapter_goal', '未设定')}\n"
        #     f"- 关键任务: {', '.join(goal_data.get('key_tasks', []))}\n"
        #     f"- 新增冲突: {goal_data.get('new_conflicts', '无')}\n"
        #     f"- 预期结果: {goal_data.get('expected_outcomes', '未设定')}\n\n"
        #     "你的职责:\n"
        #     "1. 当角色偏离主线时提供环境提示\n"
        #     "2. 解答关于场景规则的询问\n"
        #     "3. 不主动参与角色决策\n"
        #     "4. 确保讨论不超出当前章节范围"
        # )
        #
        # env_agent = AssistantAgent(
        #     name="Env_Agent",
        #     description="用于提供环境信息，不作为角色进行对话",
        #     model_client=self.model_client,
        #     system_message=env_prompt,
        # )
        # print(f"{env_agent.name} 创建成功")

        # 2. 动态创建角色 agent
        role_agents = []
        for agent_config in self.agents_config:
            # 构建每个 角色 agent 的 prompt
            # TODO： 需要根据具体的角色信息文件的格式进行调整
            role_relation = self._get_role_relation(agent_config) # 读取角色在上一章节的关系
            print(f"{role_relation}")
            role_events = self._get_role_events(agent_config) # 读取角色在上一章节所发生的事件
            print(f"{role_events}")
            role_identity = self._get_role_identity(agent_config) # 读取角色的基本信息
            print(f"{role_identity}")
            role_prompt = self._create_role_prompt(role_relation, role_events, role_identity, short_goal)

            # 获取合法的 agent name（用于内部逻辑）
            agent_id = agent_config.get("id", f"role_{len(role_agents)}")
            role_name = to_valid_identifier(agent_id)
            print(f"当前角色id{agent_id}")
            print(f"当前角色名称{role_name}")

            agent = AssistantAgent(
                name=role_name, # 要修改name读取逻辑
                model_client=self.model_client,
                system_message=role_prompt
            )
            role_agents.append(agent)

        # 3. 构建多智能体对话 team
        chat_team = RoundRobinGroupChat(
            participants=role_agents, # 组合所有将参与对话的 agent 包含 环境智能体 + 角色智能体
            max_turns=len(role_agents) * self.maxround
        )
        # 
        print(f"DEBUG - maxround类型: {type(self.maxround)}, 值: {self.maxround}")


        # 返回 智能体对话集群
        return chat_team

    def _save_chapter(self, plan):
        """
        将生成的 plan 保存为 JSON 文件，文件名格式为 chapter_N.json，
        N 为当前文件夹中最大编号 + 1。
        将知识图谱进行更新。
        保存生成章节的角色记忆为json。

        参数:
            plan (dict): 要保存的 plan 数据，应为字典格式。
            包含:
            - chapter: 章节号
            - content: 简洁版内容
            - env: 环境信息
            - agents_config: 角色配置
            - relationships: 角色关系
            - scenes: 场景信息
            - events: 事件列表
        """

        # plan["chapter"] = self.current_chapter  # 直接使用当前章节号

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
        # new_chapter_num = current_max_chapter + 1
        # new_file_name = f"chapter_{new_chapter_num}.json"
        new_file_name = f"chapter_{self.current_chapter}.json"
        new_file_path = folder_path / new_file_name

        try:
            if isinstance(plan, str):
                plan_data = json.loads(plan)
            elif isinstance(plan, dict):
                plan_data = plan
            else:
                raise ValueError("plan必须是JSON字符串或字典")

            # 将 plan 写入文件
            with open(new_file_path, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, ensure_ascii=False, indent=4, cls=CustomJSONEncoder)

            logging.info(f"新章节已保存为: {new_file_path}")

            # 更新知识图谱
            self.memory_agent.load_chapter(str(new_file_path))
            logging.info(f"知识图谱已更新")

            # 保存角色记忆
            self.memory_agent.save_character_memories(self.current_chapter)
            logging.info(f"角色记忆已保存")

        except Exception as e:
            logging.error(f"保存章节失败: {str(e)}", exc_info=True)
            raise

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
            # 静态环境数据已在__init__中加载，此处仅验证
            print(f"故事标题: {self.title}")
            print(f"长期目标: {self.longgoal}")
            print(f"初始角色数: {len(self.initial_data['characters'])}")

            # 验证必要数据是否存在
            if not all([self.title, self.longgoal, self.background]):
                raise ValueError("初始数据缺少必要字段")

        except Exception as e:
            print(f"⚠️ 初始化失败: {str(e)}")
            return
        
        print("初始化完毕\n")

        # === 2. 章节生成主循环 ===
        while True:
            chapter_num = self._get_next_chapter_number()
            print(f"\n📖 开始生成第 {chapter_num} 章...")

            # -- 2.1 生成短期目标 --
            try:
                # 构造短期目标生成提示（包含长期目标和当前环境）
                shortgoal_prompt = (
                    f"长期目标: {self.longgoal}\n"
                    f"当前环境: {json.dumps(self.background, ensure_ascii=False)}\n"
                    f"上一章的方案事件: {json.dumps(self.last_plan, ensure_ascii=False) if self.last_plan else '无'}\n"
                    f"请生成第 {chapter_num} 章的短期目标\n"
                    "输出必须是完整JSON对象，使用指定键值对：chapter_goal, chapter_title。"
                    "内容全部用中文描述，禁止使用标点或空格以外任何符号。"
                    """请严格遵循以下规则生成第 {chapter_num} 章的短期目标：
                    1. 【核心要求】
                       - chapter_goal必须≤20字，直接解决上一章的遗留问题或延续动机
                       - chapter_title必须≤10字且与chapter_goal强关联
                       - 必须推动长期目标「{self.longgoal}」的进展
    
                    2. 【内容规范】
                       - 禁止添加解释性文本
                       - 仅输出如下JSON格式：
                    {
                      "chapter_goal": "例如：揭露叛徒身份或逃离废墟城市",
                      "chapter_title": "例如：背叛者或生死逃亡"
                    }
    
                    3. 【设计原则】
                       - 从当前环境提取关键冲突元素
                       - 确保目标可执行（明确动作+对象）
                       - 必须包含1个创新悬念点"""
                )

                print(f"短期目标生成提示：\n{shortgoal_prompt}")

                # 调用短期目标智能体（直接await异步调用）
                short_goal = await self.shortgoal_agent.run(task=shortgoal_prompt)

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

            # -- 2.2 多轮方案生成 --
            round_plans = []
            for round_num in range(1, 4):  # 生成三轮不同方案
                print(f"  第 {round_num} 轮方案生成中...")

                try:
                    # 创建角色团队（包含环境智能体和所有角色智能体）
                    team = self._create_team_from_config(short_goal)

                    # 运行团队讨论（明确指定任务格式）
                    response = await team.run(
                        task=json.dumps({
                            "instruction": "生成完整故事方案",
                            "requirements": [
                                f"故事所处背景: {self.background}\n"
                                f"故事长期目标: {self.longgoal}\n"
                                "保持角色性格一致性",
                                "推进长期目标发展",
                            ]
                        })
                    )

                    # 输出响应内容（不尝试解析）
                    print(f"原始输出信息\n{response}")
                    # 提取LLM的回答
                    llm_content=extract_llm_content(response)
                    print(f"llm_content: \n{llm_content}")
                    final_content = self._process_llm_output(llm_content)
                    round_plans.append(final_content)
                    print(f"团队讨论结果\n{final_content}")
                    print(round_plans)
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

                # 保存章节数据+更新知识图谱
                self._save_chapter(best_plan)
                self.last_plan = best_plan  # 保存当前章节作为下一章的"上一章"

                # self.memory_agent.build_graph_from_json(best_plan)
            except Exception as e:
                print(f"⚠️ 方案保存失败: {str(e)}")
                continue

            # -- 2.5 长期目标检查 --
            try:
                if await self._if_get_longgoal(self.longgoal, best_plan):
                    print("🎉 故事已达成长期目标，生成完成！")
                    break
            except Exception as e:
                print(f"⚠️ 长期目标检查失败: {str(e)}")
                continue  # 继续生成下一章

        # === 3. 收尾工作 ===
        print("🏁 故事生成流程结束")
