import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from typing import Dict, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jConnector:
    """
    Neo4j数据库连接器类，用于与Neo4j数据库进行交互。
    """
    def __init__(self):
        """
        初始化Neo4j数据库连接
        该方法从环境变量中读取Neo4j数据库的URI、用户名和密码，并使用这些信息建立数据库连接
        如果未设置密码环境变量，则抛出ValueError异常
        """
        # 从环境变量中获取Neo4j数据库的URI，如果未设置，则使用默认值
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        # 从环境变量中获取Neo4j数据库的用户名，如果未设置，则使用默认值
        self.user = os.getenv("NEO4J_USERNAME", "neo4j")
        # 从环境变量中获取Neo4j数据库的密码
        self.password = os.getenv("NEO4J_PASSWORD")
        # 打印Neo4j数据库的URI、用户名和密码
        # print(self.uri, self.user, self.password)

         # 检查是否设置了密码环境变量，如果没有设置，则抛出异常
        if not self.password:
            raise ValueError("NEO4J_PASSWORD环境变量未设置")

        # 增加连接池配置
        # 使用获取到的URI、用户名和密码建立与Neo4j数据库的连接，并配置连接池
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            max_connection_lifetime=30 * 60,  # 30分钟
            max_connection_pool_size=50,
            connection_timeout=10  # 10秒
        )
        logger.info("✅ Neo4j连接器初始化完成")

    def close(self):
        """
        关闭Neo4j数据库连接。
        该方法检查是否存在一个名为'driver'的属性，如果存在，则关闭该连接，并在日志中记录关闭连接的信息。
    """
        if hasattr(self, 'driver'):
            self.driver.close()
            logger.info("Neo4j连接已关闭")

    def execute_query(self, query: str, parameters: Optional[Dict] = None):
        """
        使用给定的查询字符串和参数执行数据库查询。

        :param query: 要执行的查询字符串。
        :param parameters: 可选的参数字典，用于查询中的占位符替换。
        :return: 查询结果的数据。
        :raises: 如果查询执行失败，抛出异常。
        """
        # 创建一个会话来执行查询
        with self.driver.session() as session:
            try:
                # 在会话中运行查询，并传入参数
                result = session.run(query, parameters or {})
                # 返回查询结果的数据
                return result.data()
            except Exception as e:
                # 如果查询执行失败，记录错误日志并重新抛出异常
                logger.error(f"执行查询失败: {query[:100]}... - {str(e)}")
                raise