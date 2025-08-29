from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from Agent.Agent_Eng.InitializeAgent import create_agents, set_automated_input
import os
import json
from datetime import datetime
import asyncio
from Resource.tools.customJSONEncoder import CustomJSONEncoder
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock


class InitialWorkflow:
    """
    A workflow class that orchestrates the initialization process using a directed agent graph.
    """

    def __init__(self, model_client, test_inputs=None):
        """
        Initialize the workflow.

        Args:
            model_client: The language model client used by agents.
            test_inputs (list, optional): List of test inputs to inject automatically. Defaults to None.
        """
        self.model_client = model_client
        self.test_inputs = test_inputs or []
        self.user_proxy = None
        self.graph_flow = None
        self.graph = None
        self.extractor = None
        self.validator = None
        self.structurer = None
        self.initializer = None

    def _create_agents(self):
        """
        Create all required agents and assign them to instance variables.
        If test inputs are provided, inject them automatically.
        """
        agents = create_agents(self.model_client)
        self.user_proxy = agents["user_proxy"]
        self.extractor = agents["extractor"]
        self.validator = agents["validator"]
        self.structurer = agents["structurer"]
        self.initializer = agents["initializer"]

        # ✅ Automatically inject test inputs if provided
        if self.test_inputs:
            print("🧪 Test inputs detected, injecting test data...")
            set_automated_input(self.test_inputs)

    def _build_graph(self):
        """
        Build the directed graph (DiGraph) representing the agent workflow.
        """
        builder = DiGraphBuilder()

        # Add nodes
        builder.add_node(self.user_proxy)
        builder.add_node(self.extractor)
        builder.add_node(self.validator)
        builder.add_node(self.structurer)
        builder.add_node(self.initializer)

        # Add edges with conditions
        builder.add_edge(self.user_proxy, self.extractor)
        builder.add_edge(self.extractor, self.validator)
        builder.add_edge(
            self.validator,
            self.user_proxy,
            condition=lambda msg: "complete" not in msg.content.lower()
        )
        builder.add_edge(
            self.validator,
            self.structurer,
            condition=lambda msg: msg.content.strip().lower() == "complete"
        )
        builder.add_edge(self.structurer, self.initializer)

        # Set entry point
        builder.set_entry_point(self.user_proxy)

        # Build the graph
        self.graph = builder.build()

    def _create_graph_flow(self):
        """
        Create the GraphFlow instance with the built graph and participant agents.
        """
        self.graph_flow = GraphFlow(
            participants=[
                self.user_proxy,
                self.extractor,
                self.validator,
                self.structurer,
                self.initializer
            ],
            graph=self.graph,
            max_turns=6
        )

    async def run(self, save_dir="./Resource/memory/memory_Eng/init"):
        """
        Execute the entire workflow and save the results.

        Args:
            save_dir (str): Directory to save output files. Created if it doesn't exist.

        Returns:
            The result of the GraphFlow execution.
        """
        os.makedirs(save_dir, exist_ok=True)

        # Create agents
        print("🚀 Creating agents...")
        self._create_agents()

        # Build graph flow
        print("🧠 Building graph flow...")
        self._build_graph()
        self._create_graph_flow()

        # Execute the workflow
        print("🎬 Executing GraphFlow...")
        result = await self.graph_flow.run()

        print(result)

        # Save initializer output
        for msg in result.messages:
            if msg.source == "initializer":
                content = msg.content

                # Extract content from potential markdown code block
                save_path = os.path.join(save_dir, "init_config.json")
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"\n📦 Initialization configuration saved to {save_path}")

        # Save full result with metadata
        full_result_path = os.path.join(save_dir, "full_result.json")
        output_data = {
            "__metadata__": {
                "description": "Complete multi-agent execution result",
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0"
            },
            "data": result.model_dump()
        }
        with open(full_result_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
        print(f"\n📄 Full execution result saved to {full_result_path}")

        return result