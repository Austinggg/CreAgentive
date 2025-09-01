# Standard libraries
import json
# import logging
from pathlib import Path

# 添加以下代码来禁用 autogen_core 的 INFO 日志
import logging
logging.getLogger('autogen_core').setLevel(logging.WARNING)
logging.getLogger('autogen_core.events').setLevel(logging.WARNING)

# Autogen
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat

# Project modules
from Agent.Agent_Eng.MemoryAgent import MemoryAgent
from Agent.Agent_Eng.StoryGenAgent import create_agents
from Resource.tools.customJSONEncoder import CustomJSONEncoder
from Resource.tools.read_json import read_max_index_file
from Resource.tools.Eng.decision import evaluate_plan
from Resource.tools.extract_llm_content import extract_llm_content
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock
from Resource.tools.to_valid_identifier import to_valid_identifier
from Resource.template.storygen_prompt.Eng.shortgoal import SHORTGOAL_PROMPT_TEMPLATE
from Resource.template.storygen_prompt.Eng.role_prompt import ROLE_PROMPT_TEMPLATE
from Resource.template.write_prompt.Eng.story_template import story_plan_template, story_plan_example


class StoryGenWorkflow:
    """
    This class includes the following methods:
    1. __init__: Initialize model client, max round settings, load initial data, initialize knowledge graph connection.
    2. _load_initial_data: Load initial data file and validate its integrity.
    3. _get_next_chapter_number: Get the next chapter number.
    4. _create_agents: Create all agents.
    5. _get_role_identity: Retrieve character identity information (structured format).
    6. _get_role_relation: Retrieve character relationship network from the previous chapter (structured format).
    7. _get_role_events: Retrieve events the character participated in during the previous chapter (structured format).
    8. _create_role_prompt: Generate system prompt for role agents.
    9. _process_llm_output: Process LLM output and merge with fixed fields.
    10. _create_team_from_config: Create agent team from configuration and set up collaboration flow.
    11. _save_chapter: Save generated chapter as JSON and update knowledge graph.
    12. _if_get_longgoal: Determine whether the long-term goal has been achieved.
    """

    def __init__(self, model_client, maxround=1):
        """Initialize the workflow with model client and max round settings."""
        self.model_client = model_client  # Set model client
        self.maxround = int(maxround)  # Max conversation rounds; one round = all agents speak once
        self.memory_agent = MemoryAgent()  # Initialize knowledge graph connection
        self.memory_agent.clear_all_chapter_data()
        self.current_chapter = 0  # Chapter counter (starts from 0)

        # Load initial data (directly use chapter_0.json)
        init_file = Path("Resource") / "memory_Eng" / "story_plan" / "chapter_0.json"
        self.initial_data = self._load_initial_data(init_file)
        # 这里查看一下initial_data的格式

        # Static data storage
        self.title = self.initial_data["title"]
        self.background = self.initial_data["background"]
        self.longgoal = self.initial_data["longgoal"]
        self.agents_config = self.initial_data["characters"]  # Initial character configuration

        # Use MemoryAgent to load initial characters and relationships into knowledge graph
        self.memory_agent.load_initial_data(init_file)

        # Store the last chapter's plan
        self.last_plan = None

        # logging.info(
        #     f"Initialization completed - Title: {self.title}, "
        #     f"Number of characters: {len(self.initial_data['characters'])}, "
        #     f"Number of relationships: {len(self.initial_data['relationships'])}"
        # )

    def _load_initial_data(self, file_path: str) -> dict:
        """
        Load initial data file.

        Loads a JSON-formatted initial data file from the specified path and validates its integrity.

        Args:
            file_path (str): Path to the data file.

        Returns:
            dict: Dictionary containing the initial data.

        Raises:
            FileNotFoundError: If the data file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
            ValueError: If required fields are missing.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Initial data file not found: {file_path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            # logging.error(f"Invalid JSON format in initial data file: {str(e)}")
            raise
        except Exception as e:
            # logging.error(f"Failed to load initial data: {str(e)}")
            raise

        required_fields = ["title", "background", "longgoal", "characters", "relationships"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Initial data missing required fields: {', '.join(missing_fields)}")

        return data

    def _get_next_chapter_number(self):
        """Get the next chapter number."""
        self.current_chapter += 1
        return self.current_chapter

    def _create_agents(self):
        """Create all agents."""
        agents = create_agents(self.model_client)
        self.shortgoal_agent = agents["shortgoalAgent"]
        self.longgoal_agent = agents["longgoalAgent"]

    def _get_role_identity(self, agent_config):
        """
        Get character identity information (structured format).

        Returns:
            {
                "characters": {  # Full character data (consistent with MemoryAgent structure)
                    "id": str,
                    "name": str,
                    "age": int,
                    "gender": str,
                    "affiliations": List[str],
                    "occupation": List[str],
                    "aliases": List[str],
                    "health_status": str,
                    "personality": str,
                },
                "error": Optional[str]  # Error message if failed
            }
        """
        role_id = agent_config.get("id")
        if not role_id:
            return {"error": "Agent configuration missing ID"}

        try:
            memory = self.memory_agent.get_character_memory(role_id, max(0, self.current_chapter - 1))
            return {"characters": memory["characters"]}
        except Exception as e:
            # logging.error(f"Failed to retrieve character identity: {str(e)}")
            return {"error": str(e)}

    def _get_role_relation(self, agent_config):
        """
        Get character's relationship network from the previous chapter (structured format).

        Returns:
            {
                "relationships": [
                    {
                        "character_id": str,
                        "name": str,
                        "type": str,
                        "chapter": int,
                        "intensity": int,
                        "awareness": str,
                    },
                    ...
                ],
                "error": Optional[str]
            }
        """
        role_id = agent_config.get("id")
        if not role_id:
            return {"error": "Agent configuration missing ID"}

        try:
            memory = self.memory_agent.get_character_memory(role_id, max(0, self.current_chapter - 1))

            return {"relationships": memory["relationships"]}
        except Exception as e:
            # logging.error(f"Failed to retrieve character relationships: {str(e)}")
            return {"error": str(e)}

    def _get_role_events(self, agent_config):
        """
        Get events the character participated in during the previous chapter (structured format).

        Returns:
            {
                "events": [
                    {
                        "event_id": str,
                        "event_name": str,
                        "event_order": int,
                        "details": str,
                        "scene_id": str,
                        "scene_name": str,
                        "scene_place": str,
                        "emotional_impact": str,
                        "consequences": List[str],
                    },
                    ...
                ],
                "error": Optional[str]
            }
        """
        print(f"Agent config: {agent_config}")
        role_id = agent_config.get("id")
        if not role_id:
            return {"events": [], "error": "Agent configuration missing ID"}

        try:
            memory = self.memory_agent.get_character_memory(role_id, max(0, self.current_chapter - 1))
            if "error" in memory:
                return {"events": [], "error": memory["error"]}

            return {"events": memory["events"]}

        except Exception as e:
            # logging.error(f"Failed to retrieve character events - ID: {role_id}, Error: {str(e)}", exc_info=True)
            return {"events": [], "error": f"Event retrieval failed: {str(e)}"}

    def _create_role_prompt(self, role_relation, role_events, role_identity, short_goal):
        """
        Create system prompt for role agent.

        Args:
            role_relation (str): Character's relationship network.
            role_events (str): Events from the previous chapter.
            role_identity (str): Character's background and identity.
            short_goal (str): Short-term goal for the current chapter.

        Returns:
            str: Formatted role prompt string.
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

        print(f"Generated role prompt:\n{role_prompt}")
        return role_prompt

    def _process_llm_output(self, llm_output: str) -> dict:
        """
        Process LLM output and merge with fixed fields.

        Args:
            llm_output (str): Raw output from LLM.

        Returns:
            dict: Final structured chapter data.

        Raises:
            ValueError: If required fields are missing.
        """
        try:
            dynamic_data = json.loads(strip_markdown_codeblock(llm_output))

            required_keys = ["relationships", "scenes", "events"]
            if not all(k in dynamic_data for k in required_keys):
                raise ValueError("LLM output missing required fields")

            final_data = {
                "chapter": self.current_chapter,
                "characters": self.initial_data["characters"],
                **dynamic_data
            }

            return final_data

        except Exception as e:
            # logging.error(f"Failed to process LLM output: {str(e)}")
            raise

    def _create_team_from_config(self, short_goal):
        """
        Create agent team from configuration and build collaboration workflow.

        Args:
            short_goal (dict): Short-term goal for current chapter.

        Returns:
            RoundRobinGroupChat: Team ready for execution.
        """
        fixed = []
        for raw in self.agents_config:

            if isinstance(raw, str):  # 该语句判断是否为字符串
                fixed.append({"id": raw, "role_name": raw})
            else:
                fixed.append(raw)
        agents_config = fixed

        role_agents = []
        for agent_config in agents_config:
            # 这里要看一看agents_config的格式，详细的内容

            role_relation = self._get_role_relation(agent_config)
            print(f"Role relation: {role_relation}")
            role_events = self._get_role_events(agent_config)
            print(f"Role events: {role_events}")
            role_identity = self._get_role_identity(agent_config)
            print(f"Role identity: {role_identity}")
            # 这里要加一个上述三个变量中的键值对中的值是否为空，如果为空，要转换成字符串“None”
            if not role_relation["relationships"]:  # 如果role_relation字段里面是空的，那么就填充为None
                role_relation["relationships"] = "None"
            if not role_events["events"]:
                role_events["events"] = "None"
            if not role_identity.get("characters"):
                role_identity["characters"] = "None"
            try:
                role_prompt = self._create_role_prompt(role_relation, role_events, role_identity, short_goal)
            except Exception as e:
                print(f"⚠️ Failed to create role prompt: {str(e)}")
                continue
            agent_id = agent_config.get("id", f"role_{len(role_agents)}")
            role_name = to_valid_identifier(agent_id)
            print(f"Current role ID: {agent_id}")
            print(f"Current role name: {role_name}")

            agent = AssistantAgent(
                name=role_name,
                model_client=self.model_client,
                system_message=role_prompt
            )
            role_agents.append(agent)

        chat_team = RoundRobinGroupChat(
            participants=role_agents,
            max_turns=len(role_agents) * self.maxround
        )

        return chat_team

    def _save_chapter(self, plan):
        """
        Save generated chapter as JSON file (chapter_N.json), update knowledge graph,
        and save character memories.

        Args:
            plan (dict or str): Chapter data to save.
        """
        print("\n--- DEBUG: Entering _save_chapter function! ---")
        folder_path = Path(__file__).parent.parent.parent / "Resource" / "memory_Eng" / "story_plan"
        folder_path.mkdir(parents=True, exist_ok=True)

        new_file_name = f"chapter_{self.current_chapter}.json"
        new_file_path = folder_path / new_file_name

        try:
            if isinstance(plan, str):
                plan_data = json.loads(plan)
            elif isinstance(plan, dict):
                plan_data = plan
            else:
                raise ValueError("Plan must be a JSON string or dictionary")

            with open(new_file_path, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, ensure_ascii=False, indent=4, cls=CustomJSONEncoder)

            # logging.info(f"New chapter saved: {new_file_path}")

            self.memory_agent.load_chapter(str(new_file_path))
            # logging.info("Knowledge graph updated")

            self.memory_agent.save_character_memories(self.current_chapter)
            # logging.info("Character memories saved")

        except Exception as e:
            # logging.error(f"Failed to save chapter: {str(e)}", exc_info=True)
            raise

    async def _if_get_longgoal(self, long_goal, plan):
        """
        Determine whether the long-term goal has been achieved.

        Args:
            long_goal (str): The long-term goal description.
            plan (dict): The current chapter plan.

        Returns:
            bool: True if long-term goal is achieved, False otherwise.
        """
        response = await self.longgoal_agent.run()
        await self.longgoal_agent.model_context.clear()
        result = response if isinstance(response, str) else str(response)

        return result.strip().upper() == "YES"

    async def run(self):
        """
        Main entry point for the story generation workflow.

        Workflow:
        1. Initialize agents and data.
        2. Loop to generate each chapter.
        3. Generate three different plans per chapter and evaluate them.
        4. Check if long-term goal is reached to determine termination.
        """
        # === 1. Initialization ===
        print("🚀 Initializing agents...")
        self._create_agents()

        try:
            if not all([self.title, self.longgoal, self.background]):
                raise ValueError("Initial data missing required fields")
        except Exception as e:
            print(f"⚠️ Initialization failed: {str(e)}")
            return

        print("Initialization completed\n")

        # === 2. Chapter Generation Loop ===
        while True:
            chapter_num = self._get_next_chapter_number()
            print(f"\n📖 Generating Chapter {chapter_num}...")

            round_plans = []
            short_goal_backup = []

            # -- 2.1 Generate short-term goals --
            try:
                shortgoal_prompt = SHORTGOAL_PROMPT_TEMPLATE.format(
                    longgoal=self.longgoal,
                    background=json.dumps(self.background, ensure_ascii=False),
                    last_plan=json.dumps(self.last_plan, ensure_ascii=False) if self.last_plan else 'None',
                    chapter_num=chapter_num
                )

                print(f"Short-term goal prompt:\n{shortgoal_prompt}")

                # Generate 3 different short-term goals
                for i in range(3):
                    try:
                        short_goal = await self.shortgoal_agent.run(task=shortgoal_prompt)
                        await self.shortgoal_agent.model_context.clear()
                        short_goal = strip_markdown_codeblock(extract_llm_content(short_goal))
                        short_goal = json.loads(short_goal)

                        chapter_title = short_goal.get("chapter_title", f"Chapter {chapter_num}")
                        chapter_goal = short_goal.get("chapter_goal", "")

                        short_goal["chapter_title"] = chapter_title
                        short_goal["chapter_goal"] = chapter_goal
                        short_goal_backup.append(short_goal)

                    except json.JSONDecodeError:
                        chapter_title = f"Chapter {chapter_num}"
                        chapter_goal = ""

                    print(f"Short-term goal type: {type(chapter_goal)}")
                    print(f"Short-term goal (processed):\n{chapter_goal}")

            except Exception as e:
                print(f"⚠️ Failed to generate short-term goals: {str(e)}")
                continue

            print("\n==================== Starting multi-round plan generation ====================\n")

            # -- 2.2 Multi-round plan generation --
            counts = 0
            while counts < 3 and short_goal_backup:  # 当前章节计划生成轮数小于3且短期目标列表不为空
                short_goal_bp = short_goal_backup[counts]
            # counts在这里表示成功生成的计划数量，如果生成失败，counts就不会增加，所以会直到成功生成3个计划为止
                print(f"\n🚀 Starting round {counts + 1} plan generation...")
                try:
                    try:
                        team = self._create_team_from_config(short_goal_bp)
                    except Exception as e:
                        print(f"⚠️ Failed to create team: {str(e)}")
                        continue

                    in_task = json.dumps({
                        "instruction": "Generate complete story plan",
                        "requirements": [
                            f"Story background: {self.background}\n"
                            f"Long-term goal: {self.longgoal}\n"
                            "Maintain character consistency",
                            "Advance long-term goal development",
                        ]
                    }, ensure_ascii=False)

                    response = await team.run(task=in_task)
                    print(f"Raw output:\n{response}")

                    llm_content = extract_llm_content(response)
                    print(f"LLM content:\n{llm_content}")

                    final_content = self._process_llm_output(llm_content)
                    final_content["chapter_title"] = short_goal_bp.get("chapter_title", f"Chapter {chapter_num}")
                    final_content["chapter_goal"] = short_goal_bp.get("chapter_goal", "")
                    round_plans.append(final_content)

                    print(f"Team discussion result:\n{final_content}")
                    print(f"Round {counts + 1} completed")
                    counts += 1

                except Exception as e:
                    print(f"⚠️ Round {counts + 1} generation failed: {str(e)}")
                    continue

            # -- 2.4 Plan evaluation and save --
            if not round_plans:
                print("⚠️ No valid plans generated, skipping this chapter")
                continue

            print("🚀 Evaluating plans")
            try:
                best_plan, best_score = await evaluate_plan(round_plans, self.model_client)
                print(f"✅ Best plan score: {best_score}")
                print(f"✅ Best plan: {best_plan}")

                ordered_plan = {
                    "chapter": self.current_chapter,
                    "chapter_title": best_plan.get("chapter_title"),
                    "chapter_goal": best_plan.get("chapter_goal"),
                    "characters": self.agents_config,
                    **{k: v for k, v in best_plan.items() if k not in ["chapter", "chapter_title", "chapter_goal", "characters", "agents_config"]}
                }

                self._save_chapter(ordered_plan)
                self.last_plan = ordered_plan

            except Exception as e:
                print(f"⚠️ Failed to save plan: {str(e)}")
                continue

            # -- 2. Long-term goal check --
            try:
                if await self._if_get_longgoal(self.longgoal, best_plan):
                    print("🎉 Long-term goal achieved. Story generation completed!")
                    break
            except Exception as e:
                print(f"⚠️ Long-term goal check failed: {str(e)}")
                continue

        # === 3. Finalization ===
        print("🏁 Story generation workflow finished")