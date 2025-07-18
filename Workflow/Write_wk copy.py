from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from Agent.WriteAgent import create_agents
import os
import json
from datetime import datetime
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock
from Resource.llmclient import LLMClientManager


class WritingWorkflow:
    def __init__(self, model_client, chapters_dir, save_dir='Resource/story'):
        """
        写作工作流初始化

        :param model_client: Autogen 模型客户端实例，用于创建和调用各 Agent
        :param chapters_dir: 章节 JSON 文件所在目录路径
        :param save_dir: 写作输出目录，默认 'Resource/story'
        """
        self.model_client = model_client
        self.chapters_dir = chapters_dir
        self.save_dir = save_dir

        # 各 Agent 占位
        self.digger = None           # 挖坑判断 Agent
        self.digger_search = None    # 挖坑检索 Agent
        self.recall = None           # 回忆判断 Agent
        self.recall_search = None    # 回忆检索 Agent
        self.combiner = None         # 合并 Agent
        self.writer = None           # 写作 Agent

        # GraphFlow 组件
        self.graph = None
        self.graph_flow = None

    def _create_agents(self):
        """
        创建所有所需 Agent 实例
        返回 diggerAgent、digger_search、recallAgent、recall_search、combinerAgent、writer
        """
        agents = create_agents(self.model_client)
        self.digger = agents['diggerAgent']
        self.digger_search = agents['digger_search']
        self.recall = agents['recallAgent']
        self.recall_search = agents['recall_search']
        self.combiner = agents['combinerAgent']
        self.writer = agents['writer']

    def _build_graph(self, all_files):
        """
        构建 Autogen 并行流程图（DiGraph）

        - recall -> recall_search -> combiner
        - digger -> digger_search -> combiner
        - combiner -> writer

        条件：
        - recall分支：非第一章且 recallAgent 输出 'YES'
        - digger分支：非最后一章且 diggerAgent 输出 'YES'
        """
        builder = DiGraphBuilder()
        # 添加节点
        builder.add_node(self.recall)
        builder.add_node(self.recall_search)
        builder.add_node(self.digger)
        builder.add_node(self.digger_search)
        builder.add_node(self.combiner)
        builder.add_node(self.writer)

        first_file = all_files[0]
        last_file = all_files[-1]
        # 回忆判断
        builder.add_edge(
            self.recall, self.recall_search,
            condition=(
                f"'{first_file}' not in msg.meta['current_file'] "
                "and 'YES' in msg.to_model_text()"
            )
        )
        # 挖坑判断
        builder.add_edge(
            self.digger, self.digger_search,
            condition=(
                f"'{last_file}' not in msg.meta['current_file'] "
                "and 'YES' in msg.to_model_text()"
            )
        )
        # 检索结果汇总到 combiner
        builder.add_edge(self.recall_search, self.combiner)
        builder.add_edge(self.digger_search, self.combiner)
        # combiner -> writer
        builder.add_edge(self.combiner, self.writer)

        self.graph = builder.build()

    def _save_text(self, content, filename):
        os.makedirs(self.save_dir, exist_ok=True)
        path = os.path.join(self.save_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📦 写作成果已保存至：{path}")

    def run(self, current_file, article_type="novel"):
        """
        执行 Autogen GraphFlow 写作流程

        步骤：
        1. 验证类型
        2. 加载当前章节 JSON
        3. 创建 Agents
        4. 构建流程图
        5. 运行 GraphFlow
        6. 提取写作输出并保存
        """
        # 1. 验证类型
        t = article_type.lower()
        assert t in ['novel', 'script'], "文章类型必须为 'novel' 或 'script'"
        # 2. 加载 JSON
        files = sorted(os.listdir(self.chapters_dir))
        assert current_file in files, "指定文件不存在"
        current_path = os.path.join(self.chapters_dir, current_file)
        with open(current_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 3. 创建 Agents
        self._create_agents()
        # 4. 构建并行流程图
        self._build_graph(files)

        # 5. 构建并运行 GraphFlow
        self.graph_flow = GraphFlow(
            participants=[
                self.recall,
                self.digger,
                self.recall_search,
                self.digger_search,
                self.combiner,
                self.writer
            ],
            graph=self.graph
        )
        result = self.graph_flow.run(
            meta={
                'current_file': current_file,
                'chapter_data': data
            }
        )

        # 6. 提取写作 Agent 输出
        writer_msgs = [m for m in result.messages if m.source == self.writer.name]
        text = strip_markdown_codeblock(writer_msgs[-1].content)

        # 保存
        ext = '.md' if t == 'script' else '.txt'
        filename = f"out_{t}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        self._save_text(text, filename)
        return text


if __name__ == '__main__':

    # 获取 DeepSeek-v3 模型客户端
    client = LLMClientManager.get_client("DeepSeek-v3")

    # 实例化并运行写作工作流
    wf = WritingWorkflow(client, './Resource/chapters')
    print(wf.run('chapter_02.json', 'novel'))
