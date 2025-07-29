import os
import json
import atexit
from datetime import datetime
from neo4j import GraphDatabase
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock
from Agent.WriteAgent import create_agents
from Resource.tools.extract_llm_content import extract_llm_content
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.agents import AssistantAgent
#from Resource.tools.extract_last_text_content import extract_last_text_content
import re

class WritingWorkflow:
    """
    写作作文档工作流类，负责协调各智能体完成从章节分析到最终文本生成的全流程
    核心功能：处理章节JSON数据、调用智能体进行伏笔挖掘与回忆检索、整合数据并生成小说/剧本
    """

    def __init__(self, model_client, chapters_dir, save_dir=None, neo4j_uri="bolt://localhost:7687",
                 neo4j_user="neo4j", neo4j_password=None):
        """
        初始化工作流参数

        :param model_client: 语言模型客户端（如DeepSeek），用于智能体调用
        :param chapters_dir: 章节JSON文件存放目录（输入目录）
        :param save_dir: 生成文本的保存目录（输出目录），默认在Resource/story
        :param neo4j_uri: Neo4j数据库连接URI
        :param neo4j_user: Neo4j用户名
        :param neo4j_password: Neo4j密码（从环境变量获取）
        """
        self.model_client = model_client
        self.chapters_dir = chapters_dir
        self.save_dir = save_dir or os.path.join("Resource", "story")

        # 初始化Neo4j连接
        self.neo4j_driver = self._init_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        atexit.register(self._close_neo4j)  # 程序退出时自动关闭连接

        # 智能体初始化标记
        self.agents_initialized = False

    def _init_neo4j(self, uri, user, password):
        """
        初始化Neo4j数据库连接驱动

        :return: Neo4j驱动实例，连接失败则返回None
        """
        if not password:
            print("⚠️ Neo4j密码未提供，跳过连接初始化")
            return None

        try:
            driver = GraphDatabase.driver(
                uri,
                auth=(user, password),
                max_connection_lifetime=30 * 60,  # 连接最大存活时间30分钟
                connection_timeout=15  # 连接超时时间15秒
            )
            # 测试连接
            with driver.session() as session:
                session.run("RETURN 1")
            print("✅ Neo4j连接初始化成功")
            return driver
        except Exception as e:
            print(f"❌ Neo4j连接失败: {str(e)}")
            return None

    def _close_neo4j(self):
        """关闭Neo4j连接（程序退出时自动调用）"""
        if self.neo4j_driver:
            try:
                self.neo4j_driver.close()
                print("✅ Neo4j连接已安全关闭")
            except Exception as e:
                print(f"⚠️ Neo4j关闭异常: {str(e)}")

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
        self.memAgent = agents["memAgent"]
        self.diggerAgent = agents["diggerAgent"]
        self.recallAgent = agents["recallAgent"]
        self.novel_writer = agents["novel_writer"]
        self.script_writer = agents["script_writer"]
        self.agents_initialized = True
        print("✅ 所有智能体初始化完成")

    def _validate_article_type(self, article_type="novel"):
        """
        验证写作类型合法性

        :param article_type: 文章类型，支持"novel"（小说）或"script"（剧本）
        :return: 小写的合法类型
        :raises AssertionError: 类型不合法时抛出
        """
        article_type = article_type.lower()
        assert article_type in ["novel", "script"], "文章类型必须为 'novel' 或 'script'"
        return article_type

    def _load_json(self, file_path):
        """
        加载并解析JSON文件

        :param file_path: JSON文件路径
        :return: 解析后的字典数据
        :raises FileNotFoundError: 文件不存在时
        :raises ValueError: JSON格式错误时
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"JSON文件不存在: {file_path}")
        except json.JSONDecodeError:
            raise ValueError(f"JSON格式无效: {file_path}")

    def _load_current_chapter(self, current_chapter_file):
        """
        加载当前章节的JSON数据

        :param current_chapter_file: 章节文件名（带.json扩展名）
        :return: 章节数据字典，格式参考chapter1.json
        """
        current_path = os.path.join(self.chapters_dir, current_chapter_file)
        print(f"📖 加载章节文件: {current_path}")
        return self._load_json(current_path)

    def _get_sorted_chapter_files(self):
        """获取按章节顺序排序的所有章节文件"""
        all_files = [
            f for f in os.listdir(self.chapters_dir)
            if f.endswith('.json') and f.startswith(('chapter', 'Chapter'))
        ]
        # 按章节数字排序（假设文件名格式为chapterX.json）
        return sorted(all_files, key=lambda x: int(re.search(r'(\d+)', x).group(1)))

    def _query_neo4j_event(self, event_id):
        """增强版Neo4j查询，获取事件所有属性"""
        if not self.neo4j_driver:
            return None

        try:
            with self.neo4j_driver.session() as session:
                result = session.run(
                    """
                    MATCH (e:Event {id: $event_id})
                    RETURN properties(e) AS event_data
                    """,
                    event_id=event_id
                ).single()
                return result["event_data"] if result else None
        except Exception as e:
            print(f"⚠️ Neo4j查询失败: {str(e)}")
            return None

    # 在Writing_wk.py中添加以下方法

    def _filter_chapter_events(self, chapter_data):
        """从章节数据中提取事件信息"""
        return {
            "chapter": chapter_data.get("chapter"),
            "events": chapter_data.get("events", [])
        }

    # 在Writing_wk.py中添加/修改以下方法

    def _filter_events_only(self, chapter_data):
        """从章节数据中只提取事件信息"""
        return {
            "chapter": chapter_data.get("chapter"),
            "events": chapter_data.get("events", [])
        }

    async def _need_recall_and_load(self, current_data, current_chapter_file):
        print("\n" + "=" * 50)
        print("🔍 开始回忆事件检索流程")
        print(f"当前章节: {current_data.get('chapter', '未知')}")

        all_files = self._get_sorted_chapter_files()
        try:
            current_index = all_files.index(current_chapter_file)
        except ValueError:
            print(f"❌ 错误：找不到文件 {current_chapter_file}")
            return {"need_recall": "No", "positions": []}, []

        if current_index == 0:
            print("ℹ️ 提示：第一章无需回忆")
            return {"need_recall": "No", "positions": []}, []

        # 构建输入数据
        input_data = {
            "current_chapter": {
                "chapter": current_data["chapter"],
                "events": current_data.get("events", [])
            },
            "past_chapters": []
        }

        # 加载前序章节
        print("\n📂 加载的前序章节:")
        for fname in all_files[:current_index]:
            chapter_data = self._load_json(os.path.join(self.chapters_dir, fname))
            past_events = chapter_data.get("events", [])
            input_data["past_chapters"].append({
                "chapter": chapter_data["chapter"],
                "events": past_events
            })
            print(f"- 章节 {chapter_data['chapter']}: {len(past_events)}个事件")

        # 调用回忆Agent
        print("\n🤖 回忆Agent输入:")
        print(json.dumps(input_data, indent=2, ensure_ascii=False))

        recall_result = await self.recallAgent.a_run(task=input_data)
        raw_output = extract_llm_content(recall_result)

        print("\n💡 回忆Agent原始输出:")
        print(raw_output)

        try:
            recall_resp = json.loads(strip_markdown_codeblock(raw_output))
            print("\n✅ 解析后的回忆结果:")
            print(json.dumps(recall_resp, indent=2, ensure_ascii=False))

            recall_events = []
            if recall_resp.get("need_recall") == "Yes":
                print("\n🔎 需要回忆的事件:")
                for pos in recall_resp.get("positions", []):
                    event_id = pos["id"]
                    print(f"- 事件ID: {event_id} | 名称: {pos.get('name', '未知')}")

                    event_details = self._query_neo4j_event(event_id)
                    if event_details:
                        print(f"  查询到的属性: {list(event_details.keys())}")
                        recall_events.append(event_details)

            return recall_resp, recall_events
        except Exception as e:
            print(f"❌ JSON解析失败: {str(e)}")
            return {"need_recall": "No", "positions": []}, []

    async def _need_dig_and_load(self, current_data, current_chapter_file):
        print("\n" + "=" * 50)
        print("🔮 开始伏笔事件检索流程")
        print(f"当前章节: {current_data.get('chapter', '未知')}")

        all_files = self._get_sorted_chapter_files()
        try:
            current_index = all_files.index(current_chapter_file)
        except ValueError:
            print(f"❌ 错误：找不到文件 {current_chapter_file}")
            return {"need_dig": "No", "positions": []}, []

        if current_index == len(all_files) - 1:
            print("ℹ️ 提示：最后一章无需伏笔")
            return {"need_dig": "No", "positions": []}, []

        # 构建输入数据
        input_data = {
            "current_chapter": {
                "chapter": current_data["chapter"],
                "events": current_data.get("events", [])
            },
            "future_chapters": []
        }

        # 加载后续章节
        print("\n📂 加载的后续章节:")
        for fname in all_files[current_index + 1:]:
            chapter_data = self._load_json(os.path.join(self.chapters_dir, fname))
            future_events = chapter_data.get("events", [])
            input_data["future_chapters"].append({
                "chapter": chapter_data["chapter"],
                "events": future_events
            })
            print(f"- 章节 {chapter_data['chapter']}: {len(future_events)}个事件")

        # 调用伏笔Agent
        print("\n🤖 伏笔Agent输入:")
        print(json.dumps(input_data, indent=2, ensure_ascii=False))

        dig_result = await self.diggerAgent.a_run(task=input_data)
        raw_output = extract_llm_content(dig_result)

        print("\n💡 伏笔Agent原始输出:")
        print(raw_output)

        try:
            dig_resp = json.loads(strip_markdown_codeblock(raw_output))
            print("\n✅ 解析后的伏笔结果:")
            print(json.dumps(dig_resp, indent=2, ensure_ascii=False))

            dig_events = []
            if dig_resp.get("need_dig") == "Yes":
                print("\n🔎 需要伏笔的事件:")
                for pos in dig_resp.get("positions", []):
                    event_id = pos["id"]
                    print(f"- 事件ID: {event_id} | 名称: {pos.get('name', '未知')}")

                    event_details = self._query_neo4j_event(event_id)
                    if event_details:
                        print(f"  查询到的属性: {list(event_details.keys())}")
                        dig_events.append(event_details)

            return dig_resp, dig_events
        except Exception as e:
            print(f"❌ JSON解析失败: {str(e)}")
            return {"need_dig": "No", "positions": []}, []

    async def _combine_plans(self, current_data, dig_events, recall_events):
        """
        完整整合当前章节数据与伏笔/回忆事件

        参数:
            current_data: 当前章节完整数据(包含persons/relationships/scenes/events等)
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

        # 5. 打印详细整合报告
        self._print_integration_details(combined)

        return combined

    def _print_integration_details(self, data):
        """打印详细的整合结果"""
        print("\n📊 整合详情报告")
        print(f"=== 章节 {data['chapter']} ===")

        # 原始数据统计
        print("\n📌 原始数据:")
        print(f"- 人物: {len(data.get('persons', []))}")
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
        required_fields = ["chapter", "persons", "events", "dig_events", "recall_events"]
        for field in required_fields:
            exists = "✔️" if field in data else "❌"
            print(f"{exists} {field}: {type(data.get(field))}")

    async def _write_and_save(self, combined_data, chapter_num, article_type):
        writer = self.novel_writer if article_type == "novel" else self.script_writer
        print(f"✍️ 开始生成第{chapter_num}章 {article_type}...")

        try:
            # 调用写作智能体
            # write_result = await writer.run(task=combined_data)
            write_result = await writer.a_run(task=combined_data)
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
        current_data = self._load_current_chapter(chapter_file)
        chapter_num = current_data.get("chapter", "unknown")

        # 2. 伏笔和回忆分析
        dig_resp, dig_data = await self._need_dig_and_load(current_data, chapter_file)
        recall_resp, recall_data = await self._need_recall_and_load(current_data, chapter_file)

        # 3. 数据整合
        combined_data = await self._combine_plans(current_data, dig_data, recall_data)

        # 4. 写作并保存
        return await self._write_and_save(combined_data, chapter_num, article_type)

    async def run_all_chapters(self, article_type="novel"):
        """
        处理所有章节（按文件名排序）

        :param article_type: 文本类型（novel/script）
        """
        all_files = sorted([
            f for f in os.listdir(self.chapters_dir)
            if f.endswith('.json') and f.startswith(('chapter', 'Chapter'))
        ])

        if not all_files:
            print("❌ 未找到任何章节文件")
            return

        print(f"📑 共发现 {len(all_files)} 个章节文件，开始批量处理...")
        for i, chapter_file in enumerate(all_files, 1):
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
