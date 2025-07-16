from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from Agent.WriteAgent import create_agents
import os
import json
from datetime import datetime
import asyncio
from Resource.tools.customJSONEncoder import CustomJSONEncoder
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock


class WritingWorkflow:
    def __init__(self, model_client, test_inputs=None):
        self.model_client = model_client
        self.test_inputs = test_inputs or []
        self.user_proxy = None
        self.graph_flow = None
        self.article_type = None  # novel / script

    def _create_agents(self):
        """创建所有智能体"""
        agents = create_agents(self.model_client)
        self.memoryAgent = agents["memoryAgent"]
        self.recallAgent = agents["recallAgent"]
        self.diggerAgent = agents["diggerAgent"]
        self.combinerAgent = agents["combinerAgent"]
        self.writer = agents["writer"]
        self.recall_search = agents["recall_search"]
        self.digger_search = agents["digger_search"]



    def _build_graph(self):
        """构建有向图流程"""
        builder = DiGraphBuilder()


        # 添加节点
        builder.add_node(self.recallAgent) # 判断是否要回忆
        builder.add_node(self.diggerAgent) # 判断是否要挖坑
        builder.add_node(self.combinerAgent) # 整合回忆 和 挖坑的方案
        builder.add_node(self.writer) # 写作智能体 根据方案进行写作
        builder.add_node(self.recall_search) # 回忆相关的检索
        builder.add_node(self.digger_search) # 挖坑相关的检索

        # 回忆过程
        builder.add_edge(self.recallAgent, self.recall_search, condition='"APPROVE" in msg.to_model_text()') # 需要回忆时 进回忆相关的检索
        builder.add_edge(self.recallAgent, self.combinerAgent, condition='"RECALL" in msg.to_model_text()') # 回忆后挖坑

        # 挖坑过程
        builder.add_edge(self.diggerAgent, self.digger_search, condition='"APPROVE" in msg.to_model_text()') # 需要挖坑时 进挖坑相关的检索
        builder.add_edge(self.diggerAgent, self.combinerAgent, condition='"RECALL" in msg.to_model_text()') # 回忆后挖坑
        

        # 将 回忆 和 挖坑  的方案汇总
        builder.add_edge(self.recall_search,self.combinerAgent)
        builder.add_edge(self.digger_search,self.combinerAgent)

        # 拿整合好的方案去写作
        builder.add_edge(self.combinerAgent, self.writer)

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
                self.writer
            ],
            graph=self.graph
        )

    def run(self, article_type="novel", save_dir="./Resource/memory/writing"):
        """运行整个写作工作流并保存结果"""
        os.makedirs(save_dir, exist_ok=True)
        self.article_type = article_type.lower()

        assert self.article_type in ["novel", "script"], "文章类型必须为 'novel' 或 'script'"

        print(f"🚀 正在创建智能体（{self.article_type} 写作模式）...")
        self._create_agents()

        print("🧠 正在构建图流程...")
        self._build_graph()
        self._create_graph_flow()

        print("🎬 正在执行 GraphFlow...")
        result = asyncio.run(self.graph_flow.run())

        print(result)

        # 保存 writer 输出
        for msg in result.messages:
            if msg.source == "writer":
                content = strip_markdown_codeblock(msg.content)
                file_ext = ".md" if self.article_type == "script" else ".txt"
                save_path = os.path.join(save_dir, f"output_{self.article_type}{file_ext}")

                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"\n📦 写作成果已保存至 {save_path}")

        # 保存完整执行结果
        full_result_path = os.path.join(save_dir, "full_result.json")
        output_data = {
            "__metadata__": {
                "description": f"{self.article_type.capitalize()} 多智能体执行结果",
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0"
            },
            "data": result.model_dump()
        }
        with open(full_result_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
        print(f"\n📄 完整执行结果已保存至 {full_result_path}")

        return result