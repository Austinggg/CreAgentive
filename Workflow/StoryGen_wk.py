# 标准库
import os
import json
import asyncio
import logging
from pathlib import Path
# autogen
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
# 项目模块
from Agent.MemoryAgent import MemoryAgent
from Agent.StoryGenAgent import create_agents
from Resource.tools.customJSONEncoder import CustomJSONEncoder
from Resource.tools.read_json import read_max_index_file
from Resource.tools.decision import evaluate_plan
from Resource.tools.extract_llm_content import extract_llm_content
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock
from Resource.tools.to_valid_identifier import to_valid_identifier
from Resource.template.storygen_prompt.shortgoal import SHORTGOAL_PROMPT_TEMPLATE
from Resource.template.storygen_prompt.role_prompt import ROLE_PROMPT_TEMPLATE
from Resource.template.story_template import story_plan_template, story_plan_example



class StoryGenWorkflow:
    def __init__(self, model_client, maxround=3):
        # 设置模型客户端和最大轮次参数
        self.model_client = model_client  #设置模型客户端
        self.maxround = int(maxround)  #设置模型最大轮次参数, 所有角色智能体参与一次对话为一轮
        self.memory_agent = MemoryAgent()  # 初始化知识图谱连接
        self.memory_agent.clear_all_chapter_data()
        self.current_chapter = 0  # 添加章节计数器(从0开始)

        # 加载初始数据（直接使用原始chapter_0.json）
        # 使用Path对象处理路径
        init_file = Path("Resource") / "memory" / "story_plan" / "chapter_0.json"
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
        """
        加载初始数据文件
        
        从指定路径加载JSON格式的初始数据文件，并验证数据完整性
        
        参数:
            file_path (str): 数据文件的路径
            
        返回:
            dict: 包含初始数据的字典
            
        异常:
            FileNotFoundError: 当数据文件不存在时抛出
            json.JSONDecodeError: 当文件格式不是有效JSON时抛出
            ValueError: 当数据缺少必要字段时抛出
        """
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
        """获取下一个章节编号"""
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
        """创建角色智能体的系统提示词
        
        Args:
            role_relation (str): 角色的关系网络信息
            role_events (str): 上一章发生的事件
            role_identity (str): 角色的身份背景
            short_goal (str): 当前章节的短期目标
            
        Returns:
            str: 格式化后的角色提示词字符串，包含角色背景、目标和生成要求
        """

        template_str = json.dumps(story_plan_template, ensure_ascii=False, indent=2)
        example_str = json.dumps(story_plan_example, ensure_ascii=False, indent=2)

        role_prompt = ROLE_PROMPT_TEMPLATE.format(
            role_identity=role_identity,
            role_relation=role_relation,
            role_events=role_events,
            short_goal=short_goal,
            template_str=template_str,
            example_str=example_str
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
        # 如果 agents_config 里有字符串，就把它当成 id 和 role_name 包装成 dict
        fixed = []
        for raw in self.agents_config:
            if isinstance(raw, str):
                fixed.append({"id": raw, "role_name": raw})
            else:
                fixed.append(raw)
        agents_config = fixed
        # —— 到此结束 —— 

        # print("agents_config ==============================\n")
        # print(self.agents_config)
        # print(f"agent_config的类型:{type(self.agents_config)}")
        # print("agents_config ==============================\n")

        # 2. 动态创建角色 agent
        role_agents = []
        for agent_config in agents_config:
            # 构建每个 角色 agent 的 prompt
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

        # print(f"DEBUG - maxround类型: {type(self.maxround)}, 值: {self.maxround}")

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

        # story_plan 保存路径
        folder_path = Path(__file__).parent.parent / "Resource" / "memory" / "story_plan"
        folder_path.mkdir(parents=True, exist_ok=True)
        # 生成文件名和路径
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
        await self.longgoal_agent.model_context.clear()
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
            # print(f"故事标题: {self.title}")
            # print(f"长期目标: {self.longgoal}")
            # print(f"初始角色数: {len(self.initial_data['characters'])}")

            # 验证必要数据是否存在
            if not all([self.title, self.longgoal, self.background]):
                raise ValueError("初始数据缺少必要字段")

        except Exception as e:
            print(f"⚠️ 初始化失败: {str(e)}")
            return
        
        print("初始化完毕\n")

        # === 2. 章节生成主循环 ===
        
        # while self.current_chapter < 10: # 生成固定章节数，测试用
        while True:
            chapter_num = self._get_next_chapter_number()
            print(f"\n📖 开始生成第 {chapter_num} 章...")

            # -- 2.1 生成短期目标 --
            try:
                # 构造短期目标生成提示（包含长期目标和当前环境）
                shortgoal_prompt = SHORTGOAL_PROMPT_TEMPLATE.format(
                    longgoal=self.longgoal,
                    background=json.dumps(self.background, ensure_ascii=False),
                    last_plan=json.dumps(self.last_plan, ensure_ascii=False) if self.last_plan else '无',
                    chapter_num=chapter_num
                )
                
                print(f"短期目标生成提示：\n{shortgoal_prompt}")

                # 调用短期目标智能体（直接await异步调用）
                short_goal = await self.shortgoal_agent.run(task=shortgoal_prompt) # 获取短期目标 智能体的system prompt 的变量是否正确获取？
                await self.shortgoal_agent.model_context.clear() # 清楚短期目标智能体的记忆

                # 打印短期目标
                print(f"短期目标：\n{short_goal}")

                # 需从 autogen 的输出中剥离 shortgoal，并且要去掉 Markdown 语法
                short_goal = strip_markdown_codeblock(extract_llm_content(short_goal))
                try:
                    short_goal = json.loads(short_goal)  # 解析为JSON
                    chapter_title = short_goal.get("chapter_title", f"第{chapter_num}章")
                    chapter_goal = short_goal.get("chapter_goal", "")
                except json.JSONDecodeError:
                    chapter_title = f"第{chapter_num}章"
                    chapter_goal = ""
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
                    print(f"第 {round_num} 轮方案已保存")

                except Exception as e:
                    print(f"⚠️ 第 {round_num} 轮生成失败: {str(e)}")
                    continue

            # -- 2.4 方案评估与保存 --
            if not round_plans:
                print("⚠️ 未生成任何有效方案，跳过本章节")
                continue

            print("🚀 开始评估方案")

            try:
                # 评分并选择最佳方案
                print(f"🚀 评估中...")
                best_plan, best_score = await evaluate_plan(round_plans, self.model_client)

                print(f"✅ 最佳方案评分: {best_score}")
                print(f"✅ 最佳方案: {best_plan}")

                # 创建新的有序字典，将章节标题和目标放在最前面
                ordered_plan = {
                    "chapter": self.current_chapter,
                    "chapter_title": chapter_title,
                    "chapter_goal": chapter_goal,
                    "characters": self.agents_config,
                    **{k: v for k, v in best_plan.items() if k not in ["chapter", "chapter_title", "chapter_goal","characters","agents_config"]}
                }

                # 保存章节数据+更新知识图谱
                self._save_chapter(ordered_plan)
                self.last_plan = ordered_plan  # 保存当前章节作为下一章的"上一章"

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