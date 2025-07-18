import json
import logging
from pathlib import Path
from typing import Dict
from autogen_agentchat.agents import BaseChatAgent
from Resource.tools.kg_builder import KnowledgeGraphBuilder
from Resource.tools.neo4j_connector import Neo4jConnector

# 设置日志记录
logging.basicConfig(level=logging.INFO) # 设置日志级别为INFO
logger = logging.getLogger(__name__) # 获取当前模块的日志记录器


class MemoryAgent:
    """
    这是一个封装了小说章节数据处理、知识图谱构建与角色记忆查询的智能代理类。
    """

    def __init__(self):
        self.connector = Neo4jConnector() # 连接到 Neo4j 数据库
        self.builder = KnowledgeGraphBuilder(self.connector) # 初始化知识图谱构建器
        self.current_chapter = 0 # 初始化当前章节编号 初始为 0
        self.clear_all_chapter_data() # 清空当前知识图谱
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

            # 检查 KnowledgeGraphBuilder 类是否有构建图谱的方法
            if hasattr(self.builder, 'build_graph_from_json'):
                # 调用 KnowledgeGraphBuilder 的方法构建图谱
                self.builder.build_graph_from_json(json_path)
            else:
                # 如果没有构建图谱的方法，记录错误并返回 False
                logger.error("KnowledgeGraphBuilder 类没有 build_graph_from_json 方法")
                return False

            # 如果图谱构建成功，记录日志并返回 True
            logger.info(f"成功构建第 {self.current_chapter} 章知识图谱")
            return True
        except Exception as e:
            # 捕获异常并记录错误信息
            logger.error(f"加载章节失败: {str(e)}")
            return False

    def get_character_memory(self, person_id: str, chapter: int) -> Dict:
        
        """
        获取指定角色在特定章节的记忆

        此函数通过请求的person_id和chapter参数，调用builder的get_character_profile方法
        来获取角色的基本记忆信息，并对其进行处理和格式化，返回一个增强格式的记忆字典

        参数:
            person_id (str): 角色ID，用于指定需要获取记忆的角色
            chapter (int): 章节编号，用于指定角色在哪个章节的记忆

        返回:
            Dict: 格式化后的角色记忆字典，如果发生错误，则直接返回错误信息
        """
        # 调用builder的方法获取角色记忆信息
        memory = self.builder.get_character_profile(person_id, chapter)

        # 检查获取的记忆中是否包含错误信息，如果包含则直接返回
        if "error" in memory:
            return memory

        # 设定 从 知识图谱读取的记忆的输出格式 即 增强记忆格式
        # 增强记忆格式，包括章节、角色属性、关系和事件
        enhanced_memory = {
            "chapter": chapter,
            "character": memory["properties"],
            "relationships": [
                {
                    "target": rel["name"],
                    "type": rel["relation_type"],
                    "intensity": rel["all_properties"].get("intensity"),
                    "subtype": rel["all_properties"].get("subtype")
                } for rel in memory["relationships"]
            ],
            "events": [
                {
                    "name": event["event_name"],
                    "scene": event["scene_name"],
                    "impact": event["impact"],
                    "consequences": event["consequences"]
                } for event in memory["events"]
            ]
        }
        # 返回增强格式的记忆
        return enhanced_memory

    def process_all_chapters(self, base_path: str, pattern: str = "chapter*.json"):
        """
        批量处理所有章节文件
        
        Args:
            base_path (str): 包含章节文件的基础路径
            pattern (str): 章节文件的命名模式，默认为"chapter*.json"
        
        Yields:
            tuple: 包含章节文件名和对应人物记忆的字典

        这个方法是一个生成器函数，它会 逐个处理章节文件，每处理完一个文件后通过 yield 返回当前文件名和对应的角色记忆数据。这种方式的优点是：
        - 不需要将所有数据一次性加载到内存中，适用于处理大量文件。
        - 外部可以通过迭代的方式逐步获取每个文件的处理结果。
        """
        # 根据提供的基础路径和模式获取所有匹配的章节文件
        chapter_files = sorted(Path(base_path).glob(pattern))
        # 如果没有找到任何匹配的文件，则记录警告信息并返回
        if not chapter_files:
            logger.warning(f"未找到匹配文件: {base_path}/{pattern}")
            return

        # 保存记忆的基础文件夹
        memory_base_dir = Path("Resource\memory\character")
        # 确保记忆基础文件夹存在，如果不存在则创建
        memory_base_dir.mkdir(parents=True, exist_ok=True)

        # 遍历每个章节文件
        for file in chapter_files:
            # 加载章节内容，如果成功则继续处理
            if self.load_chapter(str(file)):
                # 获取本章所有人物ID
                with open(file, 'r', encoding='utf-8') as f:
                    persons = [p["id"] for p in json.load(f).get("persons", [])]

                # 为每个角色存储记忆
                memories = {
                    person_id: self.get_character_memory(person_id, self.current_chapter)  # 修改此处，传入当前章节号
                    for person_id in persons
                }

                # 创建章节目录
                chapter_dir = memory_base_dir / f"chapter_{self.current_chapter}_memories"
                chapter_dir.mkdir(exist_ok=True)

                # 存储每个角色的记忆到单独的JSON文件
                for person_id, memory in memories.items():
                    file_name = chapter_dir / f"{person_id}_memory.json"
                    with open(file_name, 'w', encoding='utf-8') as json_file:
                        json.dump(memory, json_file, ensure_ascii=False, indent=4)

                # 生成章节文件名和对应人物记忆的字典
                yield file.stem, memories

    def get_previous_chapters_events(self, person_id: str, current_chapter: int):
        """
        获取指定人物在所有小于当前章节编号的章节中参与的事件
    
        参数:
        person_id: str - 人物的唯一标识符
        current_chapter: int - 当前章节的编号
    
        返回:
        list - 包含人物在之前章节中参与的事件信息的列表
        """
        # 构建查询语句，以获取指定人物在当前章节之前的所有章节中参与的事件
        query = f"""
        MATCH (p:Person)-[r:IN_EVENT]->(e:Event)
        WHERE p.id = $person_id AND ANY(label IN labels(e) WHERE label STARTS WITH 'Chapter' AND toInteger(substring(label, 7)) < {current_chapter})
        RETURN e.id as event_id, e.name as event_name, e.details as details, e.order as event_order, 
               [label IN labels(e) WHERE label STARTS WITH 'Chapter'][0] as chapter_label
        ORDER BY toInteger(substring(chapter_label, 7)), event_order
        """
        # 执行查询并获取结果
        result = self.connector.execute_query(query, {"person_id": person_id})
        return result

    def get_next_chapters_events(self, person_id: str, current_chapter: int):
        """
        获取指定人物在所有大于当前章节编号的章节中参与的事件
    
        参数:
        person_id -- 人物的唯一标识符
        current_chapter -- 当前章节的编号
    
        返回:
        返回一个列表，包含指定人物在后续章节中参与的事件信息，包括事件ID、名称、详情、顺序和章节标签
        """
        # 构建查询语句，用于获取指定人物在后续章节中的事件信息
        query = f"""
        MATCH (p:Person)-[r:IN_EVENT]->(e:Event)
        WHERE p.id = $person_id AND ANY(label IN labels(e) WHERE label STARTS WITH 'Chapter' AND toInteger(substring(label, 7)) > {current_chapter})
        RETURN e.id as event_id, e.name as event_name, e.details as details, e.order as event_order, 
               [label IN labels(e) WHERE label STARTS WITH 'Chapter'][0] as chapter_label
        ORDER BY toInteger(substring(chapter_label, 7)), event_order
        """
        # 执行查询并获取结果
        result = self.connector.execute_query(query, {"person_id": person_id})
        return result

    def close(self):
        """
        关闭与Neo4j数据库的连接。

        此方法通过调用self.connector的close方法来关闭数据库连接。
        随后，记录一条信息到日志，表明Neo4j连接已关闭。
        """
        self.connector.close()  # 关闭Neo4j数据库连接
        logger.info("Neo4j连接已关闭")  # 记录连接关闭的信息到日志


# 使用示例
# if __name__ == "__main__":
    # agent = MemoryAgent()
    # try:
    #     # 修改为正确的测试数据路径
    #     CHAPTERS_PATH = "D:\Desktop\CreAgentive\resource\data\chapters"

    #     # 确保目录存在
    #     Path(CHAPTERS_PATH).mkdir(parents=True, exist_ok=True)
    #     print(f"章节数据目录: {CHAPTERS_PATH}")

    #     # 处理多章节数据
    #     for chapter_name, memories in agent.process_all_chapters(CHAPTERS_PATH):
    #         print(f"\n=== {chapter_name} 角色记忆 ===")
    #         for person_id, memory in memories.items():
    #             print(f"\n角色 {memory['character']['name']} 的记忆:")
    #             print(f"- 人际关系: {len(memory['relationships'])} 条")
    #             print(f"- 参与事件: {len(memory['events'])} 个")

    #     # 测试 get_previous_chapters_events 方法
    #     person_id = "p1"
    #     current_chapter = agent.current_chapter
    #     previous_events = agent.get_previous_chapters_events(person_id, current_chapter)
    #     print(f"\n{person_id} 在之前章节参与的事件:")
    #     for event in previous_events:
    #         print(f"章节: {event['chapter_label']}, 事件名称: {event['event_name']}, 事件顺序: {event['event_order']}")

    #     # 测试 get_next_chapters_events 方法
    #     next_events = agent.get_next_chapters_events(person_id, current_chapter)
    #     print(f"\n{person_id} 在之后章节参与的事件:")
    #     for event in next_events:
    #         print(f"章节: {event['chapter_label']}, 事件名称: {event['event_name']}, 事件顺序: {event['event_order']}")

    # finally:
    #     agent.close()