from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from Agent.InitializeAgent import create_agents, set_automated_input
import os
import json
from datetime import datetime
import asyncio
from Resource.tools.customJSONEncoder import CustomJSONEncoder
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock

class InitialWorkflow:
    def __init__(self, model_client, test_inputs=None):
        self.model_client = model_client
        self.test_inputs = test_inputs or []
        self.user_proxy = None
        self.graph_flow = None

    def _create_agents(self):
        """创建所有智能体"""
        agents = create_agents(self.model_client)
        self.user_proxy = agents["user_proxy"]
        self.extractor = agents["extractor"]
        self.validator = agents["validator"]
        self.structurer = agents["structurer"]
        self.initializer = agents["initializer"]

        # ✅ 自动注入测试输入
        if self.test_inputs:
            print("🧪 检测到 test_inputs，正在注入测试输入...")
            set_automated_input(self.test_inputs)

    def _build_graph(self):
        """构建有向图流程"""
        builder = DiGraphBuilder()

        # 添加节点
        builder.add_node(self.user_proxy)
        builder.add_node(self.extractor)
        builder.add_node(self.validator)
        builder.add_node(self.structurer)
        builder.add_node(self.initializer)

        # 添加边
        builder.add_edge(self.user_proxy, self.extractor)
        builder.add_edge(self.extractor, self.validator)
        builder.add_edge(self.validator, self.user_proxy, condition=lambda msg: "完整" not in msg.content)
        builder.add_edge(self.validator, self.structurer, condition=lambda msg: msg.content.strip() == "完整")
        builder.add_edge(self.structurer, self.initializer)

        # 设置起点
        builder.set_entry_point(self.user_proxy)

        # 构建流程
        self.graph = builder.build()

    def _create_graph_flow(self):
        """创建 GraphFlow 实例"""
        self.graph_flow = GraphFlow(
            participants=[
                self.user_proxy,
                self.extractor,
                self.validator,
                self.structurer,
                self.initializer
            ],
            graph=self.graph
        )

    def run(self, save_dir="./resource/memory/init"):
        """运行整个工作流并保存结果"""
        os.makedirs(save_dir, exist_ok=True)

        # 创建智能体
        print("🚀 正在创建智能体...")
        self._create_agents()

        # 构建图流程
        print("🧠 正在构建图流程...")
        self._build_graph()
        self._create_graph_flow()

        # 执行流程
        print("🎬 正在执行 GraphFlow...")
        result = asyncio.run(self.graph_flow.run())

        print(result)

        # 保存 initializer 输出
        for msg in result.messages:
            if msg.source == "initializer":
                content = msg.content

                # 提取JSON 代码块中的内容
                save_path = os.path.join(save_dir, "init_config.json")
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"\n📦 初始化配置已保存至 {save_path}")

        # 保存完整 result（带元数据）
        full_result_path = os.path.join(save_dir, "full_result.json")
        output_data = {
            "__metadata__": {
                "description": "完整多智能体执行结果",
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0"
            },
            "data": result.model_dump()
        }
        with open(full_result_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
        print(f"\n📄 完整执行结果已保存至 {full_result_path}")

        return result