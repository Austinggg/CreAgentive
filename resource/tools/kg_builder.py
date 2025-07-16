import json
import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from typing import Dict, List, Optional, Any
import logging
from Resource.tools.neo4j_connector import Neo4jConnector

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeGraphBuilder:
    """
    知识图谱构建器类，用于处理章节数据并构建知识图谱。
    该类负责从JSON文件加载章节数据，创建和更新人物、场景和事件节点，
    以及处理人物之间的关系。
    """

    def __init__(self, connector: Neo4jConnector):
        """
        初始化函数，设置Neo4j连接器，并在初始化时执行数据清理和约束设置。

        :param connector: Neo4j数据库连接器实例，用于执行数据库操作。
         """
        self.connector = connector
        self._clean_duplicate_data()  # 先清理重复数据
        self._setup_constraints()  # 再创建约束
        self._person_cache = {} # 缓存人物数据
        self._relationship_cache = {} # 缓存人物关系数据

    def clear_all_data(self):
        """
        清空Neo4j数据库中的所有数据
        """
        query = "MATCH (n) DETACH DELETE n"
        try:
            self.connector.execute_query(query)
            logger.info("✅ 所有数据已成功清空")
        except Exception as e:
            logger.error(f"清空数据失败: {e}")
            raise

    def _prepare_properties(self, properties: Dict, defaults: Dict) -> Dict:
        """
        准备节点/关系的属性字典，合并默认值和提供的值
    
        参数:
        properties - 提供的属性字典
        defaults - 默认属性字典
    
        合并后的属性字典，确保所有属性都包含默认值和提供的值
        """
        props = defaults.copy() # 创建默认属性的副本，以避免修改原始字典
        props.update(properties) # 更新副本以包含提供的属性，这将覆盖相同的默认属性
        # 确保列表属性始终是列表
        for key in props:
            # 如果默认值是列表，但提供的值不是列表，则将其转换为列表
            if key in defaults and isinstance(defaults[key], list) and not isinstance(props[key], list):
                # 如果属性值为None，则转换为空列表，否则将其包裹成单元素列表
                props[key] = [props[key]] if props[key] is not None else []
        # 返回合并并处理后的属性字典
        return props

    def _check_apoc_available(self) -> bool:
        """
        检查APOC插件是否可用

        APOC (A Procedure On Cypher) 是一个Neo4j图形数据库的扩展插件，提供了大量的实用函数和过程，
        用于简化数据处理、转换和与外部系统交互的过程。此函数旨在验证当前数据库连接下APOC插件是否可用。

        Returns:
            bool: 如果APOC插件可用，返回True；否则返回False。
        """
        try:
            # 尝试执行查询以获取APOC插件的版本信息
            result = self.connector.execute_query("RETURN apoc.version()")
            # 如果查询成功，返回True，表示APOC插件可用
            return bool(result)
        except Exception as e:
            # 如果查询失败，记录错误日志并返回False，表示APOC插件不可用
            logger.error("APOC插件不可用: %s", str(e))
            return False

    def _clean_duplicate_data(self):
        """
        清理重复数据
        
        该方法使用APOC插件来检测并合并图数据库中的重复节点
        仅当APOC插件可用时，才执行清理操作
        """
        if not self._check_apoc_available():
            logger.warning("APOC插件不可用，跳过重复数据清理")
            return

        # 定义一系列Cypher查询，旨在合并不同类型的重复节点
        queries = [
            # 清理重复Person节点
            """
            MATCH (p:Person)
            WITH p.id AS id, collect(p) AS nodes
            WHERE size(nodes) > 1
            CALL apoc.refactor.mergeNodes(nodes, {properties: 'combine'})
            YIELD node
            RETURN count(node)
            """,
            # 清理其他重复节点
            """
            MATCH (s:Scene)
            WITH s.id AS id, collect(s) AS nodes
            WHERE size(nodes) > 1
            CALL apoc.refactor.mergeNodes(nodes, {properties: 'combine'})
            YIELD node
            RETURN count(node)
            """,
            """
            MATCH (e:Event)
            WITH e.id AS id, collect(e) AS nodes
            WHERE size(nodes) > 1
            CALL apoc.refactor.mergeNodes(nodes, {properties: 'combine'})
            YIELD node
            RETURN count(node)
            """
        ]
        # 遍历每个查询，尝试执行并处理可能的异常
        for query in queries:
            try:
                result = self.connector.execute_query(query)
                logger.debug("清理重复数据结果: %s", result)
            except Exception as e:
                logger.warning(f"清理重复数据时出错: {e}")

    def _setup_constraints(self):
        """创建必要的约束
        
        此函数负责在数据库中设置必要的唯一性约束，以确保Person、Scene和Event标签的id属性的唯一性
        这对于维护数据的一致性和完整性至关重要
        """

        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Scene) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE"
        ]

        # 遍历约束列表，尝试执行每个约束的创建
        for query in constraints:
            try:
                # 使用connector执行查询来创建约束
                self.connector.execute_query(query)
                # 如果成功创建约束，则记录调试信息
                logger.debug("成功创建约束: %s", query)
            except Exception as e:
                # 如果创建约束失败，则记录错误信息并抛出异常
                logger.error(f"创建约束失败: {e}")
                raise

    def clear_chapter_data(self, chapter: int):
        """
        清理指定章节的所有数据
        
        这个方法通过删除与指定章节相关的所有节点和关系来清理数据
        它特别针对以下几种标签的节点和关系进行清理：
        - Person（人物）
        - Scene（场景）
        - Event（事件）
        - KNOWS（认识关系）
        - IN_EVENT（参与事件关系）
        
        参数:
        - chapter (int): 需要清理数据的章节编号
        
        返回:
        无
        """
        # 定义一系列Cypher查询以删除指定章节的所有相关数据
        queries = [
            f"MATCH (n:Person:Chapter{chapter}) DETACH DELETE n",
            f"MATCH (n:Scene:Chapter{chapter}) DETACH DELETE n",
            f"MATCH (n:Event:Chapter{chapter}) DETACH DELETE n",
            f"MATCH ()-[r:KNOWS]->() WHERE r.chapter = {chapter} DELETE r",
            f"MATCH ()-[r:IN_EVENT]->() WHERE r.chapter = {chapter} DELETE r"
        ]
        # 遍历每个查询，尝试执行删除操作
        for query in queries:
            try:
                # 使用connector执行Cypher查询
                self.connector.execute_query(query)
                # 记录调试信息，表明查询执行成功
                logger.debug("成功执行清理查询: %s", query)
            except Exception as e:
                # 如果执行查询时发生错误，记录错误信息
                logger.error(f"执行清理查询时出错: {query} - {e}")

    def load_initial_data(self, json_file: str):
        """
        加载初始数据

        本函数从指定的JSON文件中读取初始数据，并将其加载到缓存中，以便快速访问
        同时，它将人物和关系数据写入Neo4j数据库

        参数:
        json_file (str): 包含初始数据的JSON文件路径
        """

        # 打开JSON文件并加载数据
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 初始化缓存
        self._person_cache = {p['id']: p for p in data.get('persons', [])}
        self._relationship_cache = {
            f"{rel['from_id']}-{rel['to_id']}-{rel['type']}": rel
            for rel in data.get('relationships', [])
        }

        # 初始化章节编号
        chapter = 0
        # 写入Neo4j 人物和 关系
        self._update_persons(chapter)
        self._update_relationships(chapter)
        # 日志输出加载数据的结果
        logger.info(f"✅ 已加载初始数据，共 {len(self._person_cache)} 个人物和 {len(self._relationship_cache)} 条关系")

    def build_graph_from_json(self, json_path: str):
        """
        从JSON文件构建知识图谱

        调用 process_chapter方法来处理指定的JSON文件
        该方法假设JSON文件包含章节数据，并将其转换为知识图谱

        该方法通过读取和解析JSON文件中的数据，将其转换为知识图谱的结构并进行处理
        这里的JSON文件应包含构建图谱所需的所有信息，比如节点和边的数据

        参数:
        json_path (str): JSON文件的路径，用于指定要处理的文件位置

        返回:
        无返回值，但会根据JSON文件中的数据更新或创建知识图谱
        
        """
        self.process_chapter(json_path)

    def _update_persons(self, chapter: int):
        """
        批量更新人物节点

        此函数负责将缓存中的人物数据批量更新到图数据库中，为每个角色添加章节特定的标签
        
        参数:
        chapter (int): 当前章节编号，用于添加章节特定的标签

        返回:
        无
        """
        # 如果人物缓存为空，则不执行任何操作
        if not self._person_cache:
            return

        # Cypher查询语句，用于批量更新人物节点及其属性，并添加章节标签
        query = """
        UNWIND $persons AS person
        MERGE (p:Person {id: person.id})
        SET p += person.props
        WITH p
        CALL apoc.create.addLabels(p, ['Chapter' + $chapter]) YIELD node
        RETURN count(node) as count
        """

        # 准备人物数据，将每个角色的属性和ID整理成查询所需的格式
        persons_data = [{
            "id": pid,
            "props": {k: v for k, v in data.items() if k != 'id'}
        } for pid, data in self._person_cache.items()]

        # 执行Cypher查询，更新人物节点，并记录更新的人物节点数量
        try:
            result = self.connector.execute_query(query, {
                "persons": persons_data,
                "chapter": chapter
            })
            logger.debug(f"更新了 {result[0]['count']} 个人物节点")
        except Exception as e:
            logger.error(f"批量更新人物失败: {str(e)}")
            raise

    # 添加单向关系
    def _update_relationships(self, chapter: int):
        """
        批量更新关系
    
        此方法用于在知识图谱中批量更新人物之间的单向关系，
        特别是当处理大量数据时，通过减少数据库交互次数来优化性能。
        
        注意：此方法创建的是单向关系，即 A->B 不意味着 B->A
        如果需要双向关系，请在数据源中明确提供两个方向的关系记录。

        参数:
            chapter (int): 关系所在的章节编号，用于跟踪关系在故事中的发展。

        返回:
            无直接返回值，但会日志记录更新了多少条关系。
        """

        # 如果关系缓存为空，则直接返回，避免无谓的处理
        if not self._relationship_cache:
            return

        # # Cypher 查询语言，用于在 Neo4j 数据库中更新关系
        query = """
        UNWIND $rels AS rel
        MATCH (a:Person {id: rel.from_id})
        MATCH (b:Person {id: rel.to_id})
        MERGE (a)-[r:KNOWS]->(b)
        SET r += rel.props, r.chapter = $chapter
        RETURN count(r) as count
        """

        # 准备关系数据，将缓存中的关系信息提取并格式化
        rels_data = []
        for rel in self._relationship_cache.values():
            rel_data = {
                "from_id": rel['from_id'],
                "to_id": rel['to_id'],
                "props": {k: v for k, v in rel.items() if k not in ['from_id', 'to_id']}
            }
            rels_data.append(rel_data)

        # 尝试执行查询，更新数据库中的关系信息
        try:
            result = self.connector.execute_query(query, {
                "rels": rels_data,
                "chapter": chapter
            })
            # 日志记录更新了多少条关系
            logger.debug(f"更新了 {result[0]['count']} 条关系")
        except Exception as e:
            # 如果更新失败，记录错误信息并重新抛出异常
            logger.error(f"批量更新关系失败: {str(e)}")
            raise

    def create_scene(self, chapter: int, **properties):
        """
        创建/更新场景节点
        
        此函数用于在特定章节中创建或更新一个场景节点。它要求传入的属性中必须包含"id"字段，
        以确保场景的唯一性。其他场景属性如"name", "place", "time_period", "pov_character", 和 "owner"可以通过
        properties参数进行指定。如果这些属性未被指定，它们将使用默认值。

        参数:
        - chapter (int): 场景所属的章节编号
        - properties (dict): 包含场景属性的字典，必须包含"id"键

        返回:
        - result: 场景节点创建或更新的结果

        异常:
        - ValueError: 如果properties中未包含"id"属性，则抛出此异常
        """
        # 检查properties中是否包含"id"属性，如果不包含，则抛出ValueError
        if "id" not in properties:
            raise ValueError("创建Scene节点必须包含id属性")

        # 定义默认的场景属性，如果properties中未提供这些属性，将使用这些默认值
        default_props = {
            "name": None,
            "place": None,
            "time_period": "UNSPECIFIED",
            "pov_character": None,
            "owner": None
        }
        # 准备场景属性，合并默认属性和用户提供的属性
        props = self._prepare_properties(properties, default_props)

        # 构建Cypher查询，用于创建或更新场景节点
        query = f"""
        MERGE (s:Scene {{id: $id}})
        SET s:Chapter{chapter}, 
            s += $props
        RETURN s
        """
        try:
            # 执行Cypher查询，创建或更新场景节点，并返回结果
            result = self.connector.execute_query(query, {"id": props["id"], "props": props})
            # 记录创建或更新场景节点的结果
            logger.debug("创建场景 %s 结果: %s", props.get("name", props["id"]), result)
            return result
        except Exception as e:
            # 如果在执行查询时发生异常，记录错误信息并重新抛出异常
            logger.error(f"创建场景节点失败: {e}")
            raise

    def create_event(self, chapter: int, **properties):
        """
        创建事件节点并关联场景

        该方法主要用于在特定章节中创建一个事件节点，并根据提供的属性进行设置
        同时，如果事件有关联的场景或参与者，也会创建相应的关联关系

        参数:
        - chapter (int): 事件所属的章节编号
        - properties (dict): 事件的属性，必须包含'id'，可选地包含其他属性如'name', 'details', 'order', 'emotional_impact', 'consequences', 'participants', 'scene_id'等

        异常:
        如果属性中没有'id'，将抛出ValueError

        返回:
        无
        """
        # 检查是否提供了必需的'id'属性
        if "id" not in properties:
            raise ValueError("创建Event节点必须包含id属性")

        # 定义事件的默认属性值
        default_props = {
            "name": None,
            "details": None,
            "order": 0,
            "emotional_impact": "{}",  # 默认改为字符串形式的JSON
            "consequences": []
        }

        # 处理emotional_impact，如果是字典则转为JSON字符串
        if "emotional_impact" in properties and isinstance(properties["emotional_impact"], dict):
            properties["emotional_impact"] = json.dumps(properties["emotional_impact"], ensure_ascii=False)

        # 合并默认属性和传入的属性，确保所有属性都被定义
        props = self._prepare_properties(properties, default_props)

        # 创建事件节点的Cypher查询
        query = f"""
        MERGE (e:Event {{id: $id}})
        SET e:Chapter{chapter}, 
            e += $props
        RETURN e
        """

        # 执行查询并处理异常
        try:
            result = self.connector.execute_query(query, {"id": props["id"], "props": props})
            logger.debug("创建事件 %s 结果: %s", props.get("name", props["id"]), result)
        except Exception as e:
            logger.error(f"创建事件节点失败: {e}")
            raise

        # 如果有参与者，创建参与者与事件的关联关系
        for participant in props.get("participants", []):
            rel_query = """
            MERGE (p:Person {id: $person_id})
            MERGE (e:Event {id: $event_id})
            MERGE (p)-[r:IN_EVENT {chapter: $chapter}]->(e)
            RETURN r
            """
            try:
                self.connector.execute_query(rel_query, {
                    "person_id": participant,
                    "event_id": props["id"],
                    "chapter": chapter
                })
            except Exception as e:
                logger.error(f"创建参与关系失败: {participant} -> {props['id']} - {e}")

        # 如果有场景ID，将事件与场景关联
        if "scene_id" in props:
            scene_query = """
            MERGE (s:Scene {id: $scene_id})
            MERGE (e:Event {id: $event_id})
            MERGE (e)-[r:OCCURRED_IN]->(s)
            RETURN r
            """
            try:
                self.connector.execute_query(scene_query, {
                    "scene_id": props["scene_id"],
                    "event_id": props["id"]
                })
            except Exception as e:
                logger.error(f"关联场景失败: {props['id']} -> {props['scene_id']} - {e}")

    def process_chapter(self, json_file: str):
        """
        处理指定章节的JSON数据，更新缓存和Neo4j数据库。
        
        本函数首先读取和解析给定的JSON文件，然后根据文件中的数据更新内部缓存，
        包括人物和关系的缓存。接着，根据数据中的场景和事件调用相应的处理函数，
        最后更新Neo4j数据库中的信息。
        
        参数:
        json_file: str - JSON文件的路径，包含章节数据。
        """

        # 读取JSON文件
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded JSON data: {data}")

        # 获取章节号
        chapter = data['chapter']
        logger.info(f"开始处理第 {chapter} 章数据...")

        # 清理当前章节的缓存
        self._person_cache = {k: v for k, v in self._person_cache.items() if f":Chapter{chapter}" not in str(v)}
        self._relationship_cache = {k: v for k, v in self._relationship_cache.items() if v.get('chapter') != chapter}

        # 更新人物缓存
        updated_persons = set()
        for person in data.get('persons', []):
            person_id = person['id']
            if person_id in self._person_cache:
                # 合并更新属性
                self._person_cache[person_id].update(person)
                updated_persons.add(person_id)
            else:
                # 新增人物
                self._person_cache[person_id] = person
                updated_persons.add(person_id)

        # 更新关系缓存
        updated_rels = set()
        for rel in data.get('relationships', []):
            rel_key = f"{rel['from_id']}-{rel['to_id']}-{rel['type']}"
            if rel_key in self._relationship_cache:
                # 更新现有关系
                self._relationship_cache[rel_key].update(rel)
            else:
                # 新增关系
                self._relationship_cache[rel_key] = rel
            updated_rels.add(rel_key)

        # 处理场景和事件
        for scene in data.get('scenes', []):
            self.create_scene(chapter, **scene)
        for event in data.get('events', []):
            self.create_event(chapter, **event)

        # 更新Neo4j
        self._update_persons(chapter)
        self._update_relationships(chapter)

        logger.info(f"✅ 第 {chapter} 章处理完成，更新了 {len(updated_persons)} 个人物和 {len(updated_rels)} 条关系")

    def get_character_profile(self, person_id: str, chapter: int):
        """
        查询人物完整档案
        
        本函数用于根据给定的人物ID和章节号查询该人物的完整档案信息。
        档案包括以下内容：
        - 基本信息（如姓名、性别、年龄等）
        - 关系网络（与其他人物的关系类型及属性）
        - 参与的事件（事件名称、场景、情感影响等）

        参数:
        - person_id (str): 要查询的人物唯一标识符
        - chapter (int): 章节号，表示在哪个章节中查询该人物的信息

        返回:
        - dict: 包含人物基本信息、关系和参与事件的字典。如果未找到人物，则返回 {"error": "Person not found"}。
        """
        # 查询人物基本信息
        person_query = f"""
        MATCH (p:Person:Chapter{chapter} {{id: $person_id}})
        RETURN p {{.*}} as properties
        """
        person_info = self.connector.execute_query(person_query, {"person_id": person_id})

        if not person_info:
            return {"error": "Person not found"}

        # 查询人物关系
        relations_query = f"""
        MATCH (p:Person:Chapter{chapter} {{id: $person_id}})-[r]->(other:Person:Chapter{chapter})
        RETURN 
            other.id as person_id,
            other.name as name,
            type(r) as relation_type,
            properties(r) as all_properties
        """
        relations = self.connector.execute_query(relations_query, {"person_id": person_id})

        # 查询人物参与的事件
        events_query = f"""
        MATCH (p:Person:Chapter{chapter} {{id: $person_id}})-[r:IN_EVENT]->(e:Event:Chapter{chapter})-[o:OCCURRED_IN]->(s:Scene:Chapter{chapter})
        RETURN 
            e.id as event_id,
            e.name as event_name,
            e.details as details,
            e.order as event_order,
            s.id as scene_id,
            s.name as scene_name,
            s.place as scene_place,
            e.emotional_impact as emotional_impact,
            e.consequences as consequences
        ORDER BY e.order
        """

        events = self.connector.execute_query(events_query, {"person_id": person_id})

        # 处理emotional_impact字段，将其从JSON字符串转换为字典，并提取当前人物的情感影响
        for event in events:
            if event["emotional_impact"]:
                try:
                    emotions = json.loads(event["emotional_impact"])
                    event["impact"] = emotions.get(person_id, "无记录")
                except (json.JSONDecodeError, AttributeError):
                    event["impact"] = "数据格式错误"
            else:
                event["impact"] = "无记录"

        # 返回完整档案信息
        return {
            "properties": person_info[0]['properties'], # 基本信息
            "relationships": relations, # 关系网络
            "events": events    # 参与的事件及其详细信息
        }


def test_character_profile(initial_data_file: str, chapter_file: str, person_id: str):
    """
    测试人物完整档案查询功能
    
    本函数主要用于测试和展示如何通过知识图谱构建器查询特定人物的完整档案
    包括人物属性、关系和参与的事件等信息

    参数:
    initial_data_file (str): 初始数据文件路径，用于构建知识图谱的基础数据
    chapter_file (str): 章节数据文件路径，包含特定章节的信息和数据
    person_id (str): 需要查询的人物标识符
    """
    # 初始化连接
    connector = Neo4jConnector()
    builder = KnowledgeGraphBuilder(connector)

    try:
        # 加载初始数据
        logger.info(f"从 {initial_data_file} 加载初始数据...")
        builder.load_initial_data(initial_data_file)

        # 处理章节数据
        logger.info(f"从 {chapter_file} 处理章节数据...")
        builder.process_chapter(chapter_file)

        # 从章节数据中获取 chapter 值
        with open(chapter_file, 'r', encoding='utf-8') as f:
            chapter_data = json.load(f)
        chapter = chapter_data['chapter']

        # 查询人物完整档案
        logger.info(f"\n查询人物 {person_id} 的完整档案...")
        profile = builder.get_character_profile(person_id, chapter)

        if "error" in profile:
            print(f"错误: {profile['error']}")
            return

        # 打印结果
        print(f"\n=== 人物属性 ===")
        for prop, value in profile['properties'].items():
            print(f"{prop}: {value}")

        print(f"\n=== 人物关系 ===")
        for rel in profile['relationships']:
            rel_info = f"{rel['name']} ({rel['person_id']})"
            rel_info += f"\n  关系类型: {rel['relation_type']}"

            # 显示其他属性
            props = rel.get('all_properties', {})
            for prop, value in props.items():
                rel_info += f"\n  {prop}: {value}"

            print(rel_info)

        print(f"\n=== 参与事件 ===")
        for event in profile['events']:
            print(f"\n事件 #{event['event_order']}: {event['event_name']}")
            print(f"场景: {event['scene_name']} ({event.get('scene_place', '未知地点')})")
            print(f"详情: {event['details']}")
            print(f"情感影响: {event['impact']}")
            print(f"后果: {', '.join(event['consequences'])}")

    except Exception as e:
        logger.error("运行测试时发生错误: %s", str(e))
    finally:
        connector.close()


# if __name__ == "__main__":
#     # 测试完整功能
#     test_character_profile("initial_data.json", "chapter_data.json", "p1")