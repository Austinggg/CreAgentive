from Agent.WriteAgent import create_agents
import os
import json
from datetime import datetime
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock
from Resource.llmclient import LLMClientManager
from autogen_agentchat.teams import DiGraphBuilder
from Agent.WriteAgent import MergePlan

class WritingWorkflow:
    def __init__(self, model_client, chapters_dir, save_dir=None):
        """
        :param model_client: 语言模型客户端，用于创建和调用各个智能体
        :param chapters_dir: 存放章节 JSON 文件的目录路径
        :param save_dir: 写作输出目录，默认在 chapters_dir/output
        """
        self.model_client = model_client
        self.chapters_dir = chapters_dir
        # 如果未指定输出目录，则在 chapters_dir 下创建 子目录
        self.save_dir = 'Resource\story' # 故事存储源路径

        # 智能体占位符，在 _create_agents() 中初始化
        # self.diggerAgent = None      # 挖坑判断
        # self.recallAgent = None      # 回忆判断
        # self.combinerAgent = None    # 合并数据
        # self.writer = None           # 写作输出

    def _create_agents(self):
        """
        创建写作流程所需的智能体：挖坑 Agent、回忆 Agent、合并 Agent、写作 Agent
        """
        agents = create_agents(self.model_client)
        self.memAgent = agents["memAgent"]
        self.diggerAgent = agents["diggerAgent"] # 挖坑 Agent用于启动创作，设定故事大纲
        self.recallAgent = agents["recallAgent"] # 回忆 Agent负责根据故事大纲回溯相关情节和背景信息
        self.combinerAgent = agents["combinerAgent"] # 合并 Agent将不同来源的信息整合成连贯的内容
        self.novel_writer = agents["novel_writer"] # 写作 Agent执行实际的写作任务，产出文本内容
        self.script_writer = agents["script_writer"] # 写作 Agent执行实际的写作任务，产出文本内容

    def _validate_article_type(self, article_type="novel"):
        """
        验证写作类型是否合法
        :param article_type: 文章类型，"novel"（小说）或 "script"（剧本）
        :return: 校验后的文章类型（小写）
        :raises: AssertionError 如果类型不合法
        """
        article_type = article_type.lower()
        assert article_type in ["novel", "script"], "文章类型必须为 'novel' 或 'script'"
        return article_type
    
    def _load_current_chapter(self, current_chapter_file):
        """
        加载当前章节的 JSON 数据
        :param current_chapter_file: 当前章节文件名（带扩展名）
        :return: 解析后的章节数据
        """
        current_path = os.path.join(self.chapters_dir, current_chapter_file)
        print(f"📖 加载当前章节：{current_chapter_file}")
        return self._load_json(current_path)
    

    def _need_dig_and_load(self, current_data, current_chapter_file):
        """
        判断是否需要挖坑，并加载后续章节数据
        :param current_data: 当前章节数据
        :param current_chapter_file: 当前章节文件名
        :return: (need_dig, dig_data)
        """
        # 获取章节文件夹中所有文件的排序列表
        all_files = sorted(os.listdir(self.chapters_dir))
        # 判断当前章节是否为最后一章
        is_last = current_chapter_file == all_files[-1]

        if is_last:
            print("🔒 最后一章，无需挖坑")
            return False, []

        print("🔍 判断是否需要‘挖坑’...")
        # 使用挖坑代理判断当前章节是否需要挖坑
        dig_resp = self.diggerAgent.run(task=current_data)
        # 根据挖坑代理的响应决定是否需要挖坑
        need_dig = dig_resp.strip().lower() == 'yes'

        dig_data = []
        if need_dig:
            print("⛏️ 需要挖坑，加载后续章节...")
            # 加载所有后续章节的数据(MemAgent 的方法修改)
            self.memAgent.load_all_chapter_data()
            for fname in all_files:
                if fname.endswith('.json') and fname > current_chapter_file:
                    dig_data.append(self._load_json(os.path.join(self.chapters_dir, fname)))

        return need_dig, dig_data
    
    def _need_recall_and_load(self, current_data, current_chapter_file):
        """
        判断是否需要回忆，并加载前序章节数据
        :param current_data: 当前章节数据
        :param current_chapter_file: 当前章节文件名
        :return: (need_recall, recall_data)
        """

        # 获取所有章节文件列表，并按名称排序
        all_files = sorted(os.listdir(self.chapters_dir))
        # 判断当前章节是否为第一章
        is_first = current_chapter_file == all_files[0]

        if is_first:
            # 如果是第一章，则无需回忆
            print("🔒 第一章，无需回忆")
            return False, []

        print("🔍 判断是否需要‘回忆’...")
        # 运行回忆代理，判断是否需要回忆
        recall_resp = self.recallAgent.run(current_data)
        # 这个地方需要修改
        need_recall = recall_resp.strip().lower() == 'yes'

        # 如果需要回忆，则加载所有前序章节的数据
        if need_recall=="Yes":
            recall_data = self.memAgent.get_previous_chapters_events(task=current_data)


        return need_recall, recall_data
    
    # Todo 要求将 检索结果进行合并一个完整的方案,这一步的变量设置待完善
    def _merge_plans(self, need_recall, recall_data, need_dig, dig_data):
        print("🔄 合并当前章节方案...")
        
        wait_to_merge = dig_data + recall_data # 合并 回忆和挖坑 的 数据，需要统一数据格式
        merge_plan = self.combinerAgent.run(task=wait_to_merge)
        return merge_plan

    def _write_and_save(self, merged_data, article_type):
        """
        执行写作并保存结果
        :param merged_data: 合并后的数据
        :param article_type: 写作类型，"novel"（小说）或 "script"（剧本）
        :return: 写作结果文本内容
        """
        print(f"✍️ 开始写作，类型：{article_type}...")
        # 根据文章类型选择 写作 Agent
        if article_type == "novel":
            writer = self.novel_writer
        elif article_type == "script":
            writer = self.script_writer
        else:
            raise ValueError("文本格式不正确")
        
        write_resp = writer.run(task=merged_data) # Writer 写作得到该章节的写作结果
        output_text = strip_markdown_codeblock(write_resp)
        print(f"✍️ 写作完成")
        # 根据写作类型确定文件扩展名
        ext = ".md" if article_type == 'script' else '.txt'
        # 构造最终的文件名
        filename = f"output_{article_type}{ext}"
        print(f"📦 成果已保存为 {filename}")
        self._save_text(output_text, filename)

        return output_text

    def _save_text(self, content, filename):
        """
        将写作结果保存为文本文件
        :param content: 文本内容
        :param filename: 文件名（带扩展名）
        """
        # 确保保存目录存在，如果不存在则创建。exist_ok=True表示如果目录已存在则不抛出异常
        os.makedirs(self.save_dir, exist_ok=True)
        # 拼接完整文件路径
        full_path = os.path.join(self.save_dir, filename)
        # 使用上下文管理器打开文件，确保文件操作后正确关闭
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        # 打印文件保存路径   
        print(f"📦 成果已保存至 {full_path}")

    def run_all_chapters(self, article_type="novel"):
        """
        逐章处理所有章节文件，从第一章到最后章，依次执行流程并保存结果
        :param article_type: 写作类型，"novel"（小说）或 "script"（剧本）
        """
        # 获取所有章节文件并排序
        all_files = sorted(
            [f for f in os.listdir(self.chapters_dir) if f.endswith('.json')]
        )
        print(f"📑 共找到 {len(all_files)} 章节文件，开始逐章处理...")

        for chapter_file in all_files:
            print(f"\n🔄 正在处理章节：{chapter_file}")
            # 调用单章处理逻辑
            self.run_single_chapter(chapter_file, article_type=article_type)

    def run_single_chapter(self, chapter_file, article_type="novel"):
        """
        执行单章处理流程

        :param chapter_file: 当前章节文件名
        :param article_type: 文章类型
        :return: 最终写作的文本内容
        """
        # ---- 步骤 3：读取当前章节 JSON ----
        print(f"🚀 读取当前章节 JSON 文件...")
        current_data = self._load_current_chapter(chapter_file)

        # ---- 步骤 4：挖坑 & 回忆 判断 ----
        print(f"🔍 判断是否需要挖坑和回忆...")
        # 判断是否需要回忆，并加载前序章节数据
        need_recall, recall_data = self._need_recall_and_load(current_data, chapter_file) 
        # 判断是否需要挖坑，并加载后续章节数据
        need_dig, dig_data = self._need_dig_and_load(current_data, chapter_file)

        # ---- 步骤 5：合并数据 ----
        print(f"🔗 合并数据成为一个方案...")
        merged_plan = self._merge_plans(need_recall, recall_data, need_dig, dig_data)
        print(f"🔗 合并数据完成！")

        # ---- 步骤 6：写作 & 保存 ----
        output_text = self._write_and_save(merged_plan, article_type)

        return output_text

    def run(self,article_type="novel"):  # "novel" or "script"
        """
        执行写作流程：
        1. 验证写作类型
        2. 创建智能体
        3. 读取当前章节 JSON
        4. 判断是否需要‘挖坑’和/或‘回忆’
        5. 如需挖坑则加载后续章节；如需回忆则加载前序章节
        6. 将原文、挖坑结果、回忆结果统一传给合并 Agent
        7. 写作并保存结果

        :param current_chapter_file: 当前章节 JSON 文件名（相对于 chapters_dir）
        :param article_type: 写作类型，"novel"（小说）或 "script"（剧本）
        :return: 最终写作的文本内容
        """
        
        # ---- 步骤 1：验证写作类型 ----
        print(f"🚀 验证写作类型...")
        article_type = self._validate_article_type(article_type) # 验证写作类型，保存写作类型

        # ---- 步骤 2：创建智能体 ----
        print(f"🚀 创建智能体（{article_type} 模式）...")
        self._create_agents()

        # 循环写作所有的章节内容，从第一章开始
        self.run_all_chapters(article_type)



if __name__ == '__main__':
    

    client = LLMClientManager.get_client("DeepSeek-v3")
    workflow = WritingWorkflow(client, chapters_dir='./Resource/chapters')
    workflow.run(article_type='novel')
    print("写作完成！")
