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
        self._character_cache = {} # 缓存人物数据
        self._relationship_cache = {} # 缓存人物关系数据

    def clear_all_data(self):
        """
        清空Neo4j数据库中的所有数据
        """
        query = "MATCH (n) DETACH DELETE n"
        try:
            self.connector.execute_query(query,write=True)
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
            # 清理重复Character节点
            """
            MATCH (p:Character)
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

        此函数负责在数据库中设置必要的唯一性约束，以确保Character、Scene和Event标签的id属性的唯一性
        这对于维护数据的一致性和完整性至关重要
        """

        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Character) REQUIRE p.id IS UNIQUE",
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
        - Character（人物）
        - Scene（场景）
        - Event（事件）
        - IN_EVENT（参与事件关系）

        参数:
        - chapter (int): 需要清理数据的章节编号

        返回:
        无
        """
        # 定义一系列Cypher查询以删除指定章节的所有相关数据
        queries = [
            f"MATCH (n:Character:Chapter{chapter}) DETACH DELETE n",
            f"MATCH (n:Scene:Chapter{chapter}) DETACH DELETE n",
            f"MATCH (n:Event:Chapter{chapter}) DETACH DELETE n",
            f"MATCH ()-[r]-() WHERE r.chapter = {chapter} DELETE r"
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

        # 缓存初始关系（用于第0章继承）
        self._initial_relationships = data.get('relationships', [])
        self._character_cache = {p['id']: p for p in data.get('characters', [])}
        self._relationship_cache = {
            f"{rel['from_id']}-{rel['to_id']}-{rel['type']}": rel
            for rel in data.get('relationships', [])
        }

        # 初始化章节编号
        chapter = 0
        # 写入Neo4j 人物和 关系
        self._update_characters(chapter)
        self._update_relationships(chapter)
        # 日志输出加载数据的结果
        logger.info(f"✅ 已加载初始数据至知识图谱，共 {len(self._character_cache)} 个人物和 {len(self._relationship_cache)} 条关系")


    def _update_characters(self, chapter: int):
        """
        批量更新人物节点

        此函数负责将缓存中的人物数据批量更新到图数据库中，为每个角色添加章节特定的标签

        参数:
        chapter (int): 当前章节编号，用于添加章节特定的标签

        返回:
        无
        """
        # 如果人物缓存为空，则不执行任何操作
        if not self._character_cache:
            return

        # Cypher查询语句，用于批量更新人物节点及其属性，并添加章节标签
        query = """
        UNWIND $characters AS character
        MERGE (p:Character {id: character.id})
        SET p += character.props
        WITH p
        CALL apoc.create.addLabels(p, ['Chapter' + $chapter]) YIELD node
        RETURN count(node) as count
        """

        # 准备人物数据，将每个角色的属性和ID整理成查询所需的格式
        characters_data = [{
            "id": pid,
            "props": {k: v for k, v in data.items() if k != 'id'}
        } for pid, data in self._character_cache.items()]

        # 执行Cypher查询，更新人物节点，并记录更新的人物节点数量
        try:
            result = self.connector.execute_query(query, {
                "characters": characters_data,
                "chapter": chapter
            })
            logger.debug(f"更新了 {result[0]['count']} 个人物节点")
        except Exception as e:
            logger.error(f"批量更新人物失败: {str(e)}")
            raise

    # 更新关系节点
    def _update_relationships(self, chapter: int):
        """关系更新：复制前一章节关系到当前章节，然后用本章关系覆盖"""

        # 1. 如果是第0章，直接使用初始关系
        if chapter == 0:
            rels_to_update = list(self._relationship_cache.values())
        else:
            try:
                # 2. 查询上一章节所有关系
                query = f"""
                    MATCH (a:Character:Chapter{chapter - 1})-[r]->(b:Character:Chapter{chapter - 1})
                    RETURN a.id as from_id, b.id as to_id, type(r) as type, properties(r) as props
                    """
                inherited_rels = self.connector.execute_query(query) or []
                logger.info(f"从章节 {chapter - 1} 继承 {len(inherited_rels)} 条关系")

                # 3. 构建要更新的关系列表
                rels_to_update = []

                # 先添加所有继承的关系（复制到当前章节）
                for rel in inherited_rels:
                    rel_data = {
                        'from_id': rel['from_id'],
                        'to_id': rel['to_id'],
                        'type': rel['type'],
                        **rel['props']
                    }
                    # 确保关系标记为当前章节
                    rel_data['chapter'] = chapter
                    rels_to_update.append(rel_data)

                print("rels_to_update:", rels_to_update)


                # 用本章关系覆盖继承的关系
                # print(self._relationship_cache.values())
                for new_rel in self._relationship_cache.values():
                    # 确保新关系有正确的章节标记
                    new_rel['chapter'] = chapter
                    # print("new_rel:",new_rel)

                    # 查找是否已存在相同 from_id/to_id 的关系（无论类型）
                    found = False
                    # print("rels_to_update:",rels_to_update)
                    for i, existing_rel in enumerate(rels_to_update):
                        # print(i)
                        # print(existing_rel)
                        if (existing_rel['from_id'] == new_rel['from_id'] and
                                existing_rel['to_id'] == new_rel['to_id']):
                            # 覆盖现有关系（替换相同方向的关系）
                            rels_to_update[i] = new_rel
                            print("rels_to_update:",rels_to_update)
                            found = True
                            logger.info(
                                f"替换关系: {new_rel['from_id']}->{new_rel['to_id']} ({existing_rel['type']} -> {new_rel['type']})")
                            break

                    if not found:
                        # 如果是全新的关系，添加到列表
                        rels_to_update.append(new_rel)
                        logger.info(f"新增关系: {new_rel['from_id']}->{new_rel['to_id']} ({new_rel['type']})")

                print("rels_to_update:", rels_to_update)

            except Exception as e:
                logger.error(f"关系更新失败: {str(e)}")
                return

        # 4. 批量更新关系到当前章节
        query = f"""
            UNWIND $rels AS rel_data
            MATCH (a:Character:Chapter{chapter} {{id: rel_data.from_id}})
            MATCH (b:Character:Chapter{chapter} {{id: rel_data.to_id}})
            CALL apoc.merge.relationship(
                a,
                rel_data.type,
                {{  // 匹配条件：关系类型、章节、from_id、to_id
                    chapter: $chapter,
                    from_id: rel_data.from_id,
                    to_id: rel_data.to_id
                }},
                {{  // 如果匹配到，设置这些属性
                    intensity: rel_data.intensity,
                    awareness: COALESCE(rel_data.awareness, '未知'),
                    new_detail: COALESCE(rel_data.new_detail, ''),
                    reason: COALESCE(rel_data.reason, ''),
                    chapter: $chapter
                }},
                b,
                {{  // 如果没有匹配到，创建关系时的属性
                    intensity: rel_data.intensity,
                    awareness: COALESCE(rel_data.awareness, '未知'),
                    new_detail: COALESCE(rel_data.new_detail, ''),
                    reason: COALESCE(rel_data.reason, ''),
                    chapter: $chapter,
                    from_id: rel_data.from_id,
                    to_id: rel_data.to_id
                }}
            ) YIELD rel
            RETURN count(rel) as count
            """

        try:
            # 准备关系数据
            rels_data = []
            for r in rels_to_update:
                rel_data = {
                    "from_id": r["from_id"],
                    "to_id": r["to_id"],
                    "type": r["type"],
                    "intensity": r.get("intensity", 3),
                    "awareness": r.get("awareness", "未知"),
                    "new_detail": r.get("new_detail", ""),
                    "reason": r.get("reason", "")
                }
                rels_data.append(rel_data)
                print("rels_data:",rels_data)

            # 使用字符串替换来处理章节标签
            query = query.replace(":Chapter$chapter", f":Chapter{chapter}")
            print("query:", query)

            result = self.connector.execute_query(query, {
                "rels": rels_data,
                "chapter": chapter
            })
            print("result:",result)
            logger.info(f"更新了 {result[0]['count']} 条关系到章节 {chapter}")
        except Exception as e:
            logger.error(f"关系更新失败: {str(e)}")

    def cleanup_duplicate_relationships(self):
        """清理数据库中所有重复的关系"""
        query = """
        MATCH (a:Character)-[r]->(b:Character)
        WITH a, b, type(r) as relType, r.chapter as chapter, collect(r) as rels
        WHERE size(rels) > 1
        UNWIND rels[1..] AS duplicateRel
        DELETE duplicateRel
        RETURN count(duplicateRel) as deletedCount
        """
        try:
            result = self.connector.execute_query(query)
            logger.info(f"清理了 {result[0]['deletedCount']} 条重复关系")
        except Exception as e:
            logger.error(f"清理重复关系失败: {str(e)}")

    def check_chapter_relationships(self, chapter: int, show_all: bool = False):
        """检查指定章节的角色关系情况，检测重复关系

        Args:
            chapter: 要检查的章节编号
            show_all: 是否显示所有关系（默认只显示问题关系）

        Returns:
            list: 查询结果列表
        """
        query = f"""
        MATCH (a:Character:Chapter{chapter})-[r]->(b:Character:Chapter{chapter})
        RETURN 
            a.id as from_id, 
            b.id as to_id, 
            type(r) as relationship_type,
            r.intensity as intensity,
            r.awareness as awareness,
            r.chapter as chapter,
            count(r) as relationship_count
        ORDER BY from_id, to_id, relationship_type
        """

        try:
            results = self.connector.execute_query(query) or []

            print(f"\n=== 第{chapter}章关系检查 ===")
            print(f"共发现 {len(results)} 条关系记录")

            duplicate_count = 0
            normal_count = 0

            for result in results:
                count = result['relationship_count']
                if count > 1:
                    duplicate_count += 1
                    print(
                        f"⚠️  重复关系: {result['from_id']}->{result['to_id']} "
                        f"({result['relationship_type']}) - 数量: {count}"
                    )
                elif show_all:
                    normal_count += 1
                    print(
                        f"✅ 正常关系: {result['from_id']}->{result['to_id']} "
                        f"({result['relationship_type']}) - 强度: {result['intensity']}"
                    )

            # 统计信息
            print(f"\n📊 统计: {duplicate_count} 条重复关系, {len(results) - duplicate_count} 条正常关系")

            if duplicate_count > 0:
                print(f"🔍 建议: 考虑使用 MERGE 或检查关系创建逻辑")

            return results

        except Exception as e:
            print(f"❌ 查询执行失败: {str(e)}")
            return []

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
            "id": None,
            "name": None,
            "details": None,
            "scene_id": None,
            "order": 0,
            "participants": [],
            "emotional_impact": "{}",
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
            MERGE (p:Character {id: $character_id})
            MERGE (e:Event {id: $event_id})
            MERGE (p)-[r:IN_EVENT {chapter: $chapter}]->(e)
            RETURN r
            """
            try:
                self.connector.execute_query(rel_query, {
                    "character_id": participant,
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

        # 清理可能存在的重复关系
        self.cleanup_duplicate_relationships()

        # 清理当前章节的关系缓存
        self._relationship_cache = {}  # 完全清空关系缓存

        # 更新人物缓存
        updated_characters = set()
        for character in data.get('characters', []):
            character_id = character['id']
            if character_id in self._character_cache:
                # 合并更新属性
                self._character_cache[character_id].update(character)
                updated_characters.add(character_id)
            else:
                # 新增人物
                self._character_cache[character_id] = character
                updated_characters.add(character_id)

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
        self._update_characters(chapter)
        self._update_relationships(chapter)

        logger.info(f"✅ 第 {chapter} 章处理完成，更新了 {len(updated_characters)} 个人物和 {len(updated_rels)} 条关系")

    def get_character_profile(self, character_id: str, chapter: int):
        """
        查询人物完整档案

        本函数用于根据给定的人物ID和章节号查询该人物的完整档案信息。
        档案包括以下内容：
        - 基本信息（如姓名、性别、年龄等）
        - 关系网络（只返回当前人物指向他人的关系）
        - 参与的事件（事件名称、场景、情感影响等）

        参数:
        - character_id (str): 要查询的人物唯一标识符
        - chapter (int): 章节号，表示在哪个章节中查询该人物的信息

        返回:
        - dict: 包含人物基本信息、关系和参与事件的字典。如果未找到人物，则返回 {"error": "Character not found"}。
        """
        # 1. 查询基本信息
        query = f"""
                MATCH (p:Character:Chapter{chapter} {{id: $character_id}})
                RETURN p {{.*}} as properties
                """
        character_info = self.connector.execute_query(query, {"character_id": character_id})

        if not character_info:
            return {"error": "Character not found"}

        # 2. 修复关系查询 - 添加参数化查询
        rel_query = f"""
            MATCH (p:Character:Chapter{chapter} {{id: $character_id}})-[r]->(other:Character:Chapter{chapter})
            WHERE r.chapter = $chapter 
            RETURN {{
                character_id: other.id,
                name: other.name,
                type: TYPE(r),
                intensity: r.intensity,
                awareness: r.awareness,
                new_detail: r.new_detail,
                chapter: r.chapter
            }} AS relationship
            """
        relationships = self.connector.execute_query(rel_query, {
            "character_id": character_id,
            "chapter": chapter  # 添加chapter参数
        }) or []
        print("relationships:",relationships)

        # 3. 查询人物参与的事件
        events_query = f"""
                    MATCH (p:Character:Chapter{chapter} {{id: $character_id}})-[r:IN_EVENT]->(e:Event:Chapter{chapter})-[o:OCCURRED_IN]->(s:Scene:Chapter{chapter})
                    RETURN 
                        e.id as event_id,
                        e.name as event_name,
                        e.order as event_order,
                        e.details as details,
                        s.id as scene_id,
                        s.name as scene_name,
                        s.place as scene_place,
                        e.emotional_impact as emotional_impact,
                        e.consequences as consequences
                    ORDER BY e.order
                    """

        events = self.connector.execute_query(events_query, {"character_id": character_id})

        # 情感影响处理逻辑
        for event in events:
            if event["emotional_impact"]:
                try:
                    emotions = json.loads(event["emotional_impact"])
                    event["emotional_impact"] = emotions.get(character_id, "无记录")
                except (json.JSONDecodeError, AttributeError):
                    event["emotional_impact"] = "数据格式错误"
            else:
                event["emotional_impact"] = "无记录"

        return {
            "properties": character_info[0]['properties'],
            "relationships": [r["relationship"] for r in relationships],
            "events": events
        }

    def save_character_memories_kg(self, chapter: int, base_path: str = None):
        """
        保存所有角色的记忆到JSON文件

        参数:
            chapter (int): 章节编号
            base_path (str): 可选的自定义基础路径
        """
        try:
            # 确定基础路径
            if base_path is None:
                # 从当前文件所在目录计算项目根目录
                current_dir = Path(__file__).parent
                # 正确计算项目根目录（根据实际目录结构调整层级）
                project_root = current_dir.parent.parent  # 假设结构: 项目根/Resource/tools/kg_builder.py
                # 设置默认人物记忆存储目录
                base_path = project_root / "Resource" / "memory" / "character"
            else:
                # 处理自定义路径（支持字符串或Path对象）
                base_path = Path(base_path)  # 确保转换为Path对象

            # 创建章节记忆文件夹（确保基础路径正确）
            chapter_dir = base_path / f"chapter_{chapter}_memories"
            chapter_dir.mkdir(parents=True, exist_ok=True)

            # 获取本章所有人物ID
            character_ids = self.get_chapter_character_ids(chapter)

            formatted_memory = {}
            # 为每个人物保存记忆
            for character_id in character_ids:
                memory = self.get_character_profile(character_id, chapter)

                # 确保记忆格式与MemoryAgent一致
                formatted_memory = {
                    "chapter": chapter,
                    "properties": memory["properties"],
                    "relationships": memory["relationships"],
                    "events": memory["events"]
                }

                # 构建记忆文件路径
                memory_file = chapter_dir / f"{character_id}_memory.json"

                # 保存JSON文件
                with open(memory_file, 'w', encoding='utf-8') as f:
                    json.dump(formatted_memory, f, ensure_ascii=False, indent=2)

                logger.info(f"✅ 已保存角色 {character_id} 的记忆到 {memory_file}")

            return formatted_memory

        except Exception as e:
            logger.error(f"保存角色记忆失败: {str(e)}")
            raise  # 向上抛出异常，让调用方处理

    def get_chapter_character_ids(self, chapter: int) -> list:
        """
        获取指定章节的所有人物ID

        参数:
            chapter (int): 章节编号

        返回:
            list: 人物ID列表
        """
        query = f"""
        MATCH (p:Character:Chapter{chapter})
        RETURN p.id as character_id
        """
        try:
            result = self.connector.execute_query(query)
            return [record['character_id'] for record in result]
        except Exception as e:
            logger.error(f"获取章节人物ID失败: {e}")
            return []


# if __name__ == "__main__":
#     # 测试完整功能
#     test_character_profile("initial_data.json", "chapter_data.json", "p1")

# if __name__ == "__main__":
#     connector = Neo4jConnector()
#     builder = KnowledgeGraphBuilder(connector)
#     builder.clear_all_data()  # 先清空
#     builder.load_initial_data("/Users/sylvia/anaconda_projects/PythonProject/CreAgentive/Resource/memory/story_plan/initial_data.json")  # 再加载
#
#     # 查询初始数据
#     result = connector.execute_query("MATCH (n:Chapter0) RETURN count(n) AS count")
#     print("Chapter0节点数量:", result[0]["count"])
#
#     connector.close()
