from Agent.WriteAgent import create_agents
import os
import json
from datetime import datetime
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock
from Resource.llmclient import LLMClientManager


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
        self.diggerAgent = agents["diggerAgent"] # 挖坑 Agent用于启动创作，设定故事大纲
        self.recallAgent = agents["recallAgent"] # 回忆 Agent负责根据故事大纲回溯相关情节和背景信息
        self.combinerAgent = agents["combinerAgent"] # 合并 Agent将不同来源的信息整合成连贯的内容
        self.writer = agents["writer"] # 写作 Agent执行实际的写作任务，产出文本内容

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
        all_files = sorted(os.listdir(self.chapters_dir))
        is_last = current_chapter_file == all_files[-1]

        if is_last:
            print("🔒 最后一章，无需挖坑")
            return False, []

        print("🔍 判断是否需要‘挖坑’...")
        dig_resp = self.diggerAgent.run(current_data)
        need_dig = dig_resp.strip().lower() == 'yes'

        dig_data = []
        if need_dig:
            print("⛏️ 需要挖坑，加载后续章节...")
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
        all_files = sorted(os.listdir(self.chapters_dir))
        is_first = current_chapter_file == all_files[0]

        if is_first:
            print("🔒 第一章，无需回忆")
            return False, []

        print("🔍 判断是否需要‘回忆’...")
        recall_resp = self.recallAgent.run(current_data)
        need_recall = recall_resp.strip().lower() == 'yes'

        recall_data = []
        if need_recall:
            print("🔄 需要回忆，加载前序章节...")
            for fname in all_files:
                if fname.endswith('.json') and fname < current_chapter_file:
                    recall_data.append(self._load_json(os.path.join(self.chapters_dir, fname)))

        return need_recall, recall_data

    def _save_text(self, content, filename):
        """
        将写作结果保存为文本文件
        :param content: 文本内容
        :param filename: 文件名（带扩展名）
        """
        os.makedirs(self.save_dir, exist_ok=True)
        full_path = os.path.join(self.save_dir, filename)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📦 成果已保存至 {full_path}")

    def run(self, current_chapter_file, article_type="novel"):  # "novel" or "script"
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


        # Todo: 打包成循环从第一章以此读取，写作

        # ---- 步骤 3：读取当前章节 JSON ----
        
        current_data = self._load_current_chapter(current_chapter_file)

        # ---- 步骤 4：挖坑 & 回忆 判断 ----
        # 回忆只在非第一章启用
        all_files = sorted(os.listdir(self.chapters_dir))
        is_first = current_chapter_file == all_files[0]
        if is_first:
            print("🔒 第一章，无需回忆")
            need_recall = False
        else:
            print("🔍 判断是否需要‘回忆’...")
            recall_resp = self.recallAgent.run(current_data)
            need_recall = recall_resp.strip().lower() == 'yes'

        # 挖坑在非最后一章启用，最后一章无需挖坑
        is_last = current_chapter_file == all_files[-1]
        if is_last:
            print("🔒 最后一章，无需挖坑")
            need_dig = False
        else:
            print("🔍 判断是否需要‘挖坑’...")
            dig_resp = self.diggerAgent.run(current_data)
            need_dig = dig_resp.strip().lower() == 'yes'

        # ---- 步骤 5：加载前序与后续章节 ----
        recall_data = []
        dig_data = []
        all_files = sorted(os.listdir(self.chapters_dir))

        if need_recall:
            print("🔄 需要回忆，加载前序章节...")
            for fname in all_files:
                if fname.endswith('.json') and fname < current_chapter_file:
                    recall_data.append(self._load_json(os.path.join(self.chapters_dir, fname)))

        if need_dig:
            print("⛏️ 需要挖坑，加载后续章节...")
            for fname in all_files:
                if fname.endswith('.json') and fname > current_chapter_file:
                    dig_data.append(self._load_json(os.path.join(self.chapters_dir, fname)))

        # ---- 步骤 6：合并所有内容 ----
        print("🔧 合并原文、回忆和挖坑数据...")
        merge_input = {
            "current": current_data,
            "recall": recall_data,
            "dig": dig_data
        }
        comb_resp = self.combinerAgent.run(merge_input)
        merged_data = json.loads(comb_resp)

        # ---- 步骤 7：写作 & 保存 ----
        print(f"✍️ 开始写作，类型：{article_type}...")
        write_prompt = {"type": article_type, "data": merged_data}
        write_resp = self.writer.run(write_prompt)
        output_text = strip_markdown_codeblock(write_resp)

        ext = ".md" if article_type == 'script' else '.txt'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"output_{article_type}_{timestamp}{ext}"
        self._save_text(output_text, filename)

        return output_text


if __name__ == '__main__':
    

    client = LLMClientManager.get_client("DeepSeek-v3")
    workflow = WritingWorkflow(client, chapters_dir='./Resource/chapters')
    workflow.run('chapter_02.json', article_type='novel')
    print("写作完成！")
