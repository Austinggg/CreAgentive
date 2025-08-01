import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict
from Resource.tools.kg_builder import KnowledgeGraphBuilder
from Resource.tools.neo4j_connector import Neo4jConnector

# 设置日志记录
logging.basicConfig(level=logging.INFO)  # 设置日志级别为INFO
logger = logging.getLogger(__name__)  # 获取当前模块的日志记录器


class MemoryAgent:
    """
    这是一个封装了小说章节数据处理、知识图谱构建与角色记忆查询的智能代理类。
    """

    def __init__(self):
        self.connector = Neo4jConnector()  # 连接到 Neo4j 数据库
        self.builder = KnowledgeGraphBuilder(self.connector)  # 初始化知识图谱构建器
        self.current_chapter = 0  # 初始化当前章节编号 初始为 0
        print("MemoryAgent初始化完成")
        logger.info("MemoryAgent初始化完成")

    def clear_all_chapter_data(self):
        """
        清除所有章节的数据
        遍历章节编号 1 到 999，调用图谱构建器清除每个章节的数据。
        """
        # 默认最大章节号为 999，可根据实际需求调整范围。
        for chapter in range(1, 1000):
            self.builder.clear_chapter_data(chapter)

    def load_initial_data(self, json_file: str):
        """
        调用KnowledgeGraphBuilder的初始数据加载方法

        从指定的JSON文件中读取初始数据，包括人物和关系信息，
        并将其加载到知识图谱中，作为第0章的基础数据。

        参数:
            json_file (str): 包含初始数据的JSON文件路径
        """
        try:
            # 检查JSON文件是否存在
            if not Path(json_file).exists():
                raise FileNotFoundError(f"初始数据JSON文件不存在: {json_file}")

            else: self.builder.load_initial_data(json_file)

            # 日志输出加载结果
            logger.info(
                f"✅ 已加载初始数据，共 {len(self.builder._character_cache)} 个人物和 {len(self.builder._relationship_cache)} 条关系")
            return True
        except Exception as e:
            logger.error(f"加载初始数据失败: {str(e)}")
            return False


    def load_chapter(self, json_path: str) -> bool:
        """
        加载并构建章节知识图谱
        从指定 JSON 文件中加载章节数据，并调用图谱构建器将其导入 Neo4j 图数据库。

        参数:
        json_path (str): JSON 文件路径，包含章节数据。

        返回:
        bool: 如果章节知识图谱构建成功，则返回 True，否则返回 False。
        """
        try:
            # 检查 JSON 文件是否存在
            if not Path(json_path).exists():
                raise FileNotFoundError(f"JSON文件不存在: {json_path}")

            # 打开并读取 JSON 文件内容
            with open(json_path, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
                self.current_chapter = chapter_data["chapter"]

            # 处理章节数据（更新Neo4j）
            self.builder.process_chapter(json_path)

            # 如果图谱构建成功，记录日志并返回 True
            logger.info(f"成功构建第 {self.current_chapter} 章知识图谱")
            return True
        except Exception as e:
            # 捕获异常并记录错误信息
            logger.error(f"加载章节失败: {str(e)}")
            return False

    def get_event(self, event_id: str) -> Dict:
        """
        获取指定事件的所有属性

        通过事件ID查询事件节点，返回该事件的所有属性

        参数:
            event_id (str): 要查询的事件ID

        返回:
            Dict: 包含事件所有属性的字典，如果事件不存在则返回错误信息
        """
        query = """
        MATCH (e:Event {id: $event_id})
        RETURN properties(e) as event_properties
        """
        params = {"event_id": event_id}

        try:
            result = self.connector.execute_query(query, params)
            if not result:
                return {"error": f"事件ID {event_id} 不存在"}

            event_properties = result[0]["event_properties"]
            logger.info(f"成功获取事件 {event_id} 的属性")
            return event_properties

        except Exception as e:
            error_msg = f"获取事件属性失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
        
    def get_event_details(self, event_id: str) -> Dict:
        """
        获取指定事件的details属性内容

        通过事件ID查询事件节点，返回该事件的details属性

        参数:
            event_id (str): 要查询的事件ID

        返回:
            Dict: 包含事件details属性的字典，如果事件不存在或没有details属性则返回错误信息
        """
        query = """
        MATCH (e:Event {id: $event_id})
        RETURN e.details as event_details
        """
        params = {"event_id": event_id}

        try:
            result = self.connector.execute_query(query, params)
            if not result:
                return {"error": f"事件ID {event_id} 不存在"}

            # 检查details属性是否存在
            event_details = result[0].get("event_details")
            if event_details is None:
                return {"error": f"事件ID {event_id} 没有details属性"}

            logger.info(f"成功获取事件 {event_id} 的details属性")
            return {"details": event_details}

        except Exception as e:
            error_msg = f"获取事件details属性失败: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_character_memory(self, character_id: str, chapter: int) -> Dict:
        """
        获取指定角色在特定章节的记忆

        此函数通过请求的character_id和chapter参数，调用builder的get_character_profile方法
        来获取角色的基本记忆信息，并对其进行处理和格式化，返回一个增强格式的记忆字典

        参数:
            character_id (str): 角色ID，用于指定需要获取记忆的角色
            chapter (int): 章节编号，用于指定角色在哪个章节的记忆

        返回:
            Dict: 格式化后的角色记忆字典，如果发生错误，则直接返回错误信息
        """
        # 调用builder的方法获取角色记忆信息
        memory = self.builder.get_character_profile(character_id, chapter)

        # 检查获取的记忆中是否包含错误信息，如果包含则直接返回
        if "error" in memory:
            return memory

        # 设定 从 知识图谱读取的记忆的输出格式 即 增强记忆格式
        # 增强记忆格式，包括章节、角色属性、关系和事件
        enhanced_memory = {
            "chapter": chapter,
            "characters": memory["properties"],
            "relationships": memory["relationships"],
            "events": memory["events"]
        }
        # 返回增强格式的记忆
        return enhanced_memory

    def save_character_memories(self, chapter: int, base_path: str = None):
        """
        查找输入章节下的所有角色记忆
        保存输入章节下的所有角色记忆到JSON文件

        参数:
            chapter (int): 章节编号
            base_path (str): 可选的自定义基础路径
        """
        try:
            # 使用知识图谱构建器的方法保存记忆
            self.builder.save_character_memories_kg(chapter, base_path)
            logger.info(f"成功保存第{chapter}章的角色记忆")
        except Exception as e:
            logger.error(f"保存角色记忆失败: {str(e)}")
            raise


    def get_previous_chapters_events(self, character_id: str, current_chapter: int):
        """
        从已保存的角色记忆中获取前五章的事件
        如果当前章节<=5，则返回从第1章到当前章节前一章的所有事件
        """
        previous_events = []

        # 限制事件数量
        limit = 2

        # 确定查询范围
        start_chapter = max(1, current_chapter - 2)
        end_chapter = current_chapter - 1

        # 遍历范围内的每一章
        for chapter in range(start_chapter, end_chapter + 1):
            try:
                # 获取该章节的角色记忆
                memory = self.get_character_memory(character_id, chapter)
                if memory and "events" in memory:
                    # 为每个事件添加章节信息
                    for event in memory["events"]:
                        event["chapter_num"] = chapter
                        event["chapter_label"] = f"Chapter{chapter}"
                    previous_events.extend(memory["events"])
            except Exception as e:
                logger.error(f"获取第{chapter}章记忆失败: {str(e)}")

        # 按章节和事件顺序排序
        previous_events.sort(key=lambda x: (x["chapter_num"], x.get("event_order", 0)))

        # 如果设置了限制数量，则返回限制数量的事件
        if limit is not None:
            previous_events = previous_events[:limit]

        return previous_events

    def get_next_chapters_events(self, current_chapter: int, end_chapter: int):
        """
        获取当前章节后最多5章中的所有事件（增强兼容性版本）
        """
        # 限制事件数量
        limit = 2

        if current_chapter >= end_chapter:
            return []

        # 更健壮的查询方案
        query = """
        MATCH (e:Event)
        // 提取所有Chapter开头的标签
        WITH e, [label IN labels(e) WHERE label STARTS WITH 'Chapter'] AS chapter_labels
        WHERE size(chapter_labels) > 0
        // 提取纯数字部分（兼容各种Chapter标签格式）
        WITH e, chapter_labels[0] AS chapter_label,
             toInteger(apoc.text.replace(chapter_labels[0], '[^0-9]', '')) AS chapter_num
        WHERE chapter_num > $current_chapter 
              AND chapter_num <= $max_chapter
        RETURN e.id as event_id, e.name as event_name, e.details as details,
               e.order as event_order, chapter_label
        ORDER BY chapter_num, e.order
        """
        params = {
            "current_chapter": current_chapter,
            "max_chapter": min(current_chapter + 2, end_chapter)
        }

        try:
            result = self.connector.execute_query(query, params)
            logger.info(f"查询第{current_chapter}章后事件: 条件{params} 结果{len(result)}条")

            # 如果设置了限制数量，则返回限制数量的事件
            if limit is not None:
                result = result[:limit]

            return result
        except Exception as e:
            logger.error(f"查询后续章节事件失败: {str(e)}")
            return []

    def close(self):
        """
        关闭与Neo4j数据库的连接
        """
        self.connector.close()  # 关闭Neo4j数据库连接
        logger.info("Neo4j连接已关闭")  # 记录连接关闭的信息到日志
