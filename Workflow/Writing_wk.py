import os
import json
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock
from Agent.WriteAgent import create_agents
from Resource.tools.extract_llm_content import extract_llm_content
from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import UnboundedChatCompletionContext
from Agent.MemoryAgent import MemoryAgent
from Resource.tools.read_json import read_json

import re

class WritingWorkflow:
    """
    写作作文档工作流类，负责协调各智能体完成从章节分析到最终文本生成的全流程
    核心功能：处理章节JSON数据、调用智能体进行伏笔挖掘与回忆检索、整合数据并生成小说/剧本
    """

    def __init__(self, model_client):
        """
        初始化工作流参数
        :param model_client: 语言模型客户端（如DeepSeek），用于智能体调用
    """
        self.model_client = model_client 
        self.chapters_dir = os.path.join("Resource", "memory", "story_plan")
        self.save_dir = os.path.join("Resource", "story")
        self.current_chapter = 0
        self.chapter_count = 0
        self.memory_agent = MemoryAgent()

        # 智能体初始化标记
        self.agents_initialized = False

    def _create_agents(self):
        """
        创建并初始化所有需要的智能体
        智能体列表：
        - memAgent: 内存管理智能体
        - diggerAgent: 伏笔挖掘智能体
        - recallAgent: 回忆检索智能体
        - novel_writer: 小说写作智能体
        - script_writer: 剧本写作智能体
        """
        if self.agents_initialized:
            return  # 避免重复初始化

        agents = create_agents(self.model_client)
        self.diggerAgent = agents["diggerAgent"]
        self.recallAgent = agents["recallAgent"]
        self.novel_writer = agents["novel_writer"]
        self.script_writer = agents["script_writer"]
        self.agents_initialized = True
        print("✅ 所有智能体初始化完成")

    def _validate_article_type(self, article_type):
        """
        验证写作类型合法性

        :param article_type: 文章类型，支持"novel"（小说）或"script"（剧本）
        :return: 小写的合法类型
        :raises AssertionError: 类型不合法时抛出
        """
        article_type = article_type.lower()
        assert article_type in ["novel", "script"], "文章类型必须为 'novel' 或 'script'"
        return article_type

    def _load_current_chapter(self, current_chapter_file):
        """
        加载当前章节的JSON数据

        :param current_chapter_file: 章节文件名（带.json扩展名）
        :return: 章节数据字典，格式参考chapter1.json
        """
        current_path = os.path.join(self.chapters_dir, current_chapter_file)
        print(f"📖 加载章节文件: {current_path}")
        data = read_json(current_path)

        return data

    async def _need_recall_and_load(self, current_data):
        print("\n" + "=" * 50)
        print("🔍 开始分人物回忆检索流程")

        # 获取所有人物
        characters = current_data.get("characters", [])
        all_recall_events = []

        for character in characters:
            char_id = character["id"]
            print(f"\n👤 处理人物: {character.get('name')} ({char_id})")

            # 获取该人物在前序章节的事件
            prev_events = self.memory_agent.get_previous_chapters_events(
                character_id=char_id,
                current_chapter=current_data["chapter"]
            )
            print(f"prev_events: {prev_events}")
            print(f"prev_events数量: {len(prev_events)}")

            if not prev_events:
                print(f"⚠️ 人物 {character.get('name')} 无前序章节事件")
                continue

            # 构建分人物输入数据
            input_data = {
                "current_character": character,
                "current_events": [
                    e for e in current_data.get("events", [])
                    if char_id in e.get("participants", [])
                ],
                "past_events": prev_events
            }
            print(f"input_data: {input_data}")

            # 调用回忆Agent
            recall_result = await self.recallAgent.a_run(task=input_data)
            # 清空 recallAgent 的上下文
            await self.recallAgent.model_context.clear()
            raw_output = extract_llm_content(recall_result)
            print(f"raw_output: {raw_output}")

            try:
                recall_resp = json.loads(strip_markdown_codeblock(raw_output))
                if recall_resp.get("need_recall") == "Yes":
                    print(f"✅ 需要为 {character.get('name')} 添加回忆:")
                    for pos in recall_resp.get("positions", []):
                        event_details = self.memory_agent.get_event_details(pos["id"])
                        if event_details:
                            event_details["related_character"] = char_id
                            event_details["recall_reason"] = pos["reason"]
                            all_recall_events.append(event_details)
            except Exception as e:
                print(f"❌ 处理人物 {character.get('name')} 回忆失败: {str(e)}")

        return {"need_recall": "Yes" if all_recall_events else "No"}, all_recall_events

    async def _need_dig_and_load(self, current_data):
        print("\n" + "=" * 50)
        print("🔮 开始伏笔事件检索流程")

        # 获取所有后续章节事件（不限定人物）
        next_events = self.memory_agent.get_next_chapters_events(
            current_chapter=current_data["chapter"],
            end_chapter=self.chapter_count  # 查看后续5章
        )
        print("next_events:", next_events)

        if not next_events:
            print("ℹ️ 无后续章节事件可供挖掘")
            return {"need_dig": "No"}, []

        # 构建输入数据
        input_data = {
            "current_chapter": current_data,
            "future_events": next_events
        }

        # 调用伏笔Agent
        dig_result = await self.diggerAgent.a_run(task=input_data)
        # 清空 diggerAgent 上下文
        await self.diggerAgent.model_context.clear()
        raw_output = extract_llm_content(dig_result)

        try:
            dig_resp = json.loads(strip_markdown_codeblock(raw_output))
            dig_events = []
            if dig_resp.get("need_dig") == "Yes":
                for pos in dig_resp.get("positions", []):
                    event_details = self.memory_agent.get_event_details(pos["id"])
                    if event_details:
                        dig_events.append(event_details)
                        # 该函数返回的内容dig_resp是一个字典，包含是否需要挖掘伏笔的标志和具体位置，
                        # 比如{"need_dig": "Yes", "positions": [{"id": "event123", "reason": "Foreshadowing for climax"}]}
                        # 其中positions是一个列表，包含了需要挖掘伏笔的事件ID和挖掘理由。
                        # 返回的dig_events是一个列表，包含了从Neo4j数据库中查询到的具体伏笔事件的详细信息，
                        # 比如[{"id": "event123", "description": "A mysterious stranger appears", ...}]。

            return dig_resp, dig_events
        except Exception as e:
            print(f"❌ 伏笔分析失败: {str(e)}")
            return {"need_dig": "No"}, []

    async def _combine_plans(self, current_data, dig_events, recall_events):
        """
        完整整合当前章节数据与伏笔/回忆事件

        参数:
            current_data: 当前章节完整数据(包含characters/relationships/scenes/events等)
            dig_events: 从后续章节提取的完整伏笔事件列表
            recall_events: 从前序章节提取的完整回忆事件列表

        返回:
            整合后的完整章节数据，保持原始结构并添加dig_events和recall_events
        """
        print("\n" + "=" * 50)
        print("🧩 开始完整数据整合")

        # 1. 深拷贝当前章节数据
        combined = json.loads(json.dumps(current_data))

        # 2. 添加完整事件信息
        combined["dig_events"] = []
        combined["recall_events"] = []

        # 3. 处理伏笔事件（从后续章节提取的完整事件）
        for event in dig_events or []:
            if isinstance(event, dict):
                # 补充必要字段（如果Neo4j查询结果缺少）
                event.setdefault("source_type", "dig")
                combined["dig_events"].append(event)

        # 4. 处理回忆事件（从前序章节提取的完整事件）
        for event in recall_events or []:
            if isinstance(event, dict):
                event.setdefault("source_type", "recall")
                combined["recall_events"].append(event)

        # 5. 与初始化设定结合
        init_data = self._load_current_chapter("chapter_0.json")
        combined = {
            "title": init_data["title"],  # 小说标题
            "background": init_data["background"],  # 世界观设定
            "init_relationships": init_data["relationships"],
            **current_data,  # 当前章节数据
            "dig_events": dig_events or [],
            "recall_events": recall_events or []
        }

        # 6. 打印详细整合报告
        self._print_integration_details(combined)

        return combined

    def _print_integration_details(self, data):
        """打印详细的整合结果"""
        print("\n📊 整合详情报告")
        print(f"=== 章节 {data.get('chapter', '未知')} ===")

        print("\n📌 原始设定:")
        print(f"- 题目: {len(data.get('title', []))}")
        print(f"- 背景: {len(data.get('background', []))}")

        # 原始数据统计
        print("\n📌 章节数据:")
        print(f"- 人物: {len(data.get('characters', []))}")
        print(f"- 关系: {len(data.get('relationships', []))}")
        print(f"- 场景: {len(data.get('scenes', []))}")
        print(f"- 主事件: {len(data.get('events', []))}")

        # 伏笔事件详情
        print("\n🔮 伏笔事件:")
        for event in data.get("dig_events", [])[:2]:  # 最多显示2个完整事件
            print(json.dumps(event, indent=2, ensure_ascii=False))

        # 回忆事件详情
        print("\n📜 回忆事件:")
        for event in data.get("recall_events", [])[:2]:
            print(json.dumps(event, indent=2, ensure_ascii=False))

        # 完整数据结构验证
        print("\n✅ 最终数据结构验证:")
        required_fields = ["chapter", "characters", "events", "dig_events", "recall_events"]
        for field in required_fields:
            exists = "✔️" if field in data else "❌"
            print(f"{exists} {field}: {type(data.get(field))}")

    async def _write_and_save(self, combined_data, chapter_num, article_type):
        
        # 选择
        writer = self.novel_writer if article_type == "novel" else self.script_writer
        print(f"✍️ 开始生成第{chapter_num}章 {article_type}...")

        try:
            # 根据文章体裁调用对应类别的写作智能体

            write_result = await writer.a_run(task=combined_data)
            # 调用完成后要求清空该 agent 的上下文
            print("调用写作智能体结束")
            await self.novel_writer.model_context.clear()
            await self.script_writer.model_context.clear()


            # print(write_result.messages)
            print("\n======================\n")
            print(f"✍️ 第{chapter_num}章 {article_type}生成完成")
            print(write_result)

            # 提取输出
            raw_output = extract_llm_content(write_result)

            # 打印原始输出
            print("\n💡 写作Agent原始输出:")
            print(raw_output)

            # 移除Markdown代码块
            output_text = strip_markdown_codeblock(raw_output)
            output_text = output_text.strip()  # 清理首尾空白

            chapter_title = combined_data.get("chapter_title", f"第{chapter_num}章")
            output_text = f"{chapter_title}\n\n{output_text}"  # 在生成内容前添加标题

            # 验证提取结果（增加明确长度检查）
            if not output_text or len(output_text) < 10:  # 避免极短无效内容
                raise ValueError(
                    f"提取的文本内容无效 "
                    f"| 原始长度: {len(raw_output)} "
                    f"| 清理后长度: {len(output_text)}"
                )

            # 保存文件
            ext = ".txt" if article_type == "novel" else ".md"
            filename = f"chapter_{chapter_num}_{article_type}{ext}"
            self._save_text(output_text, filename)
            print(f"📦 已保存至: {os.path.join(self.save_dir, filename)}")

            return output_text

        except Exception as e:
            print(f"⚠️ 写作失败: {str(e)}")
            # 保存完整调试信息
            debug_info = (
                f"错误: {str(e)}\n"
                f"原始结果类型: {type(write_result)}\n"
                f"原始结果内容: {str(write_result)}\n"
                f"extract_llm_content输出: {raw_output}\n"
                f"strip后内容: {output_text if 'output_text' in locals() else '未定义'}"
            )
            self._save_text(debug_info, f"chapter_{chapter_num}_debug.txt")
            return ""

    def _save_text(self, content, filename):
        """
        保存文本内容到指定文件

        :param content: 文本内容
        :param filename: 保存的文件名
        """
        os.makedirs(self.save_dir, exist_ok=True)
        full_path = os.path.join(self.save_dir, filename)

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"📦 已保存至: {full_path}")

    async def run_single_chapter(self, chapter_file, article_type="novel"):
        """
        处理单个章节的完整流程

        输入:
            chapter_file: 章节文件名（如chapter1.json）
            article_type: 文本类型（novel/script）

        输出:
            生成的章节文本内容
        """
        # 1. 加载当前章节数据
        current_data = self._load_current_chapter(chapter_file)  # 加载章节数据
        chapter_num = current_data.get("chapter", "unknown")  # 获取章节编号

        # 2. 伏笔和回忆分析
        dig_resp, dig_data = await self._need_dig_and_load(current_data)
        # dig_resp和dig_data的
        recall_resp, recall_data = await self._need_recall_and_load(current_data)
        print(dig_resp)
        print(dig_data)
        print(recall_resp)
        print(recall_data)

        # 3. 数据整合
        # 这里的_combine_plans函数会将当前章节数据与挖掘到的伏笔事件和回忆事件进行整合
        combined_data = await self._combine_plans(current_data, dig_data, recall_data)
        print(combined_data)

        # 4. 写作并保存
        return await self._write_and_save(combined_data, chapter_num, article_type)

    async def run_all_chapters(self, article_type="novel"):
        """
        处理所有章节（按文件名排序）
        :param article_type: 文本类型（novel/script）
        """

        print(f"检查目录: {self.chapters_dir}")
        print(f"目录内容: {os.listdir(self.chapters_dir)}")

        # 获取所有章节文件并排除chapter_0.json
        all_files = [
            f for f in os.listdir(self.chapters_dir)
            if f.endswith('.json')
               and f != "chapter_0.json"  # 更宽松的条件
        ]

        # 按章节数字排序（假设文件名格式为chapterX.json）
        all_files = sorted(all_files, key=lambda x: int(re.search(r'(\d+)', x).group(1)))

        self.chapter_count = len(all_files)
        print(f"📑 共发现 {len(all_files)} 个章节文件（跳过chapter_0.json），开始批量处理...")
        # 现在开始处理每个章节，调用函数run_single_chapter进行处理
        for i, chapter_file in enumerate(all_files, 1):
            self.current_chapter = i
            print(f"\n===== 处理第{i}/{len(all_files)}章: {chapter_file} =====")
            await self.run_single_chapter(chapter_file, article_type)


    async def run(self, article_type="novel"):
        """
        启动完整写作流程
        :param article_type: 文本类型（novel/script）
        """
        # 1. 验证输入类型
        article_type = self._validate_article_type(article_type)

        # 2. 初始化智能体
        self._create_agents()
        if self.novel_writer is None:
            raise ValueError("小说写作智能体未正确初始化")

        # 3. 处理所有章节
        await self.run_all_chapters(article_type)

        print("\n🎉 所有章节处理完成！")


# # 运行示例
# if __name__ == '__main__':
#     import asyncio
#     from dotenv import load_dotenv
#     from Resource.llmclient import LLMClientManager

#     # 加载环境变量
#     load_dotenv()


#     async def main():
#         # 配置路径
#         project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#         chapters_dir = os.path.join(project_root, "Resource", "memory", "story_plan")

#         # 获取模型客户端和Neo4j密码
#         llm_client = LLMClientManager().get_client("deepseek-v3")
#         neo4j_password = os.getenv("NEO4J_PASSWORD")

#         # 初始化并运行工作流
#         workflow = WritingWorkflow(
#             model_client=llm_client,
#             chapters_dir=chapters_dir,
#             neo4j_password=neo4j_password
#         )
#         await workflow.run(article_type="novel")  # 可切换为"script"


#     asyncio.run(main())
