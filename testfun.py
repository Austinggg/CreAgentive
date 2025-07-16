from Resource.tools.kg_builder import KnowledgeGraphBuilder
from Resource.tools.neo4j_connector import Neo4jConnector


connector = Neo4jConnector()
kg_builder = KnowledgeGraphBuilder(connector=connector)
kg_builder._check_apoc_available()