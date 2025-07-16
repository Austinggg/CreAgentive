import os
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient
from neo4j import GraphDatabase
import atexit
from llmclient import LLMClientManager

# 加载环境变量
load_dotenv()

# --- 获取环境变量 ---
neo4j_password = os.getenv("NEO4J_PASSWORD")

# 验证必需配置
if not neo4j_password:
    raise ValueError("必须配置 NEO4J_PASSWORD 环境变量")

# --- DeepSeek 客户端 ---
DeepSeek_client = LLMClientManager().get_client("deepseek-v3")

# --- Neo4j 连接 ---
neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(
        os.getenv("NEO4J_USERNAME", "neo4j"),
        neo4j_password
    ),
    max_connection_lifetime=30 * 60,
    max_connection_pool_size=50,
    connection_timeout=15,
    encrypted=False
)

# 测试 Neo4j 连接
try:
    with neo4j_driver.session() as session:
        session.run("RETURN 1").single()
    print("✅ Neo4j 连接成功")
except Exception as e:
    print(f"❌ Neo4j 连接失败: {e}")
    neo4j_driver = None

# 安全关闭
atexit.register(lambda: neo4j_driver.close() if neo4j_driver else None)

print("✅ DeepSeek 和 Neo4j 客户端初始化完成")