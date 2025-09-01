import json
import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from typing import Dict, List, Optional, Any
import logging
from Resource.tools.neo4j_connector import Neo4jConnector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeGraphBuilder:
    """
    Knowledge graph builder class for processing chapter data and constructing a knowledge graph.
    This class is responsible for loading chapter data from JSON files, creating and updating character, scene, and event nodes,
    and handling relationships between characters.
    The methods included in this class are:
    - __init__: Initialization function, sets up the Neo4j connector, and performs data cleanup and constraint setup during initialization.
    - clear_all_data: Clears all data in the Neo4j database.
    - load_initial_data: Loads initial data from a JSON file, including character and relationship information.
    - process_chapter: Processes the JSON data for a specified chapter, updates the cache, and the Neo4j database.
    - create_scene: Creates or updates a scene node.
    - create_event: Creates an event node and associates it with a scene.
    - get_character_profile: Queries the complete profile of a character.
    - clear_chapter_data: Clears all data for a specified chapter.
    - _update_characters: Updates character nodes in bulk.
    - _update_relationships: Updates character relationships in bulk.
    - _prepare_properties: Prepares the property dictionary for nodes/relationships, merging default values with provided values.
    - _check_apoc_available: Checks if the APOC plugin is available.
    - _clean_duplicate_data: Cleans up duplicate data.
    - _setup_constraints: Creates necessary constraints.
    This class relies on the Neo4jConnector class to perform actual database operations.
    """

    def __init__(self, connector: Neo4jConnector):
        """
        Initialization function, sets up the Neo4j connector, and performs data cleanup and constraint setup during initialization.

        :param connector: Neo4j database connector instance, used for database operations.
         """
        self.connector = connector
        self._clean_duplicate_data()  # Clean up duplicate data first
        self._setup_constraints()  # Then create constraints
        self._character_cache = {} # Cache character data
        self._relationship_cache = {} # Cache character relationship data

    def clear_all_data(self):
        """
        Clears all data in the Neo4j database
        """
        query = "MATCH (n) DETACH DELETE n"
        try:
            self.connector.execute_query(query,write=True)
            logger.info("✅ All data has been successfully cleared")
        except Exception as e:
            logger.error(f"Failed to clear data: {e}")
            raise

    def _prepare_properties(self, properties: Dict, defaults: Dict) -> Dict:
        """
        Prepares the property dictionary for nodes/relationships, merging default values with provided values

        Parameters:
        properties - Provided property dictionary
        defaults - Default property dictionary

        Returns:
        The merged property dictionary, ensuring all properties include default values and provided values
        """
        props = defaults.copy() # Create a copy of the default properties to avoid modifying the original dictionary
        props.update(properties) # Update the copy with provided properties, which will override matching default properties
        # Ensure list properties are always lists
        for key in props:
            # If the default value is a list but the provided value is not a list, convert it to a list
            if key in defaults and isinstance(defaults[key], list) and not isinstance(props[key], list):
                # If the property value is None, convert to an empty list; otherwise, wrap it in a single-element list
                props[key] = [props[key]] if props[key] is not None else []
        # Return the merged and processed property dictionary
        return props

    def _check_apoc_available(self) -> bool:
        """
        Checks if the APOC plugin is available

        APOC (A Procedure On Cypher) is an extension plugin for the Neo4j graph database, providing a large number of utility functions and procedures
        for simplifying data processing, transformation, and interaction with external systems. This function is intended to verify the availability of the APOC plugin under the current database connection.

        Returns:
            bool: Returns True if the APOC plugin is available; otherwise, returns False.
        """
        try:
            # Attempt to execute a query to retrieve the version information of the APOC plugin
            result = self.connector.execute_query("RETURN apoc.version()")
            # If the query succeeds, return True, indicating the APOC plugin is available
            return bool(result)
        except Exception as e:
            # If the query fails, log the error and return False, indicating the APOC plugin is unavailable
            logger.error("APOC plugin unavailable: %s", str(e))
            return False

    def _clean_duplicate_data(self):
        """
        Cleans up duplicate data

        This method uses the APOC plugin to detect and merge duplicate nodes in the graph database
        Cleanup is performed only if the APOC plugin is available
        """
        if not self._check_apoc_available():
            logger.warning("APOC plugin unavailable, skipping duplicate data cleanup")
            return

        # Define a series of Cypher queries aimed at merging duplicate nodes of different types
        queries = [
            # Clean up duplicate Character nodes
            """
            MATCH (p:Character)
            WITH p.id AS id, collect(p) AS nodes
            WHERE size(nodes) > 1
            CALL apoc.refactor.mergeNodes(nodes, {properties: 'combine'})
            YIELD node
            RETURN count(node)
            """,
            # Clean up other duplicate nodes
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
        # Iterate over each query, attempting execution and handling possible exceptions
        for query in queries:
            try:
                result = self.connector.execute_query(query)
                logger.debug("Cleanup duplicate data result: %s", result)
            except Exception as e:
                logger.warning(f"Error during duplicate data cleanup: {e}")

    def _setup_constraints(self):
        """Creates necessary constraints

        This function is responsible for setting up the necessary uniqueness constraints in the database to ensure the uniqueness of the id property
        for the Character, Scene, and Event labels. This is crucial for maintaining data consistency and integrity.
        """

        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Character) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Scene) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE"
        ]

        # Iterate over the constraint list, attempting to execute the creation of each constraint
        for query in constraints:
            try:
                # Use the connector to execute the query to create the constraint
                self.connector.execute_query(query)
                # If the constraint is successfully created, log debug information
                logger.debug("Successfully created constraint: %s", query)
            except Exception as e:
                # If creating the constraint fails, log the error information and raise an exception
                logger.error(f"Failed to create constraint: {e}")
                raise

    def clear_chapter_data(self, chapter: int):
        """
        Clears all data for a specified chapter

        This method clears data by deleting all nodes and relationships related to the specified chapter
        It specifically targets nodes and relationships with the following labels:
        - Character (characters)
        - Scene (scenes)
        - Event (events)
        - IN_EVENT (participation in event relationships)

        Parameters:
        - chapter (int): The chapter number for which data needs to be cleared

        Returns:
        None
        """
        # Define a series of Cypher queries to delete all related data for the specified chapter
        queries = [
            f"MATCH (n:Character:Chapter{chapter}) DETACH DELETE n",
            f"MATCH (n:Scene:Chapter{chapter}) DETACH DELETE n",
            f"MATCH (n:Event:Chapter{chapter}) DETACH DELETE n",
            f"MATCH ()-[r]-() WHERE r.chapter = {chapter} DELETE r"
        ]
        # Iterate over each query, attempting to execute the deletion operation
        for query in queries:
            try:
                # Use the connector to execute the Cypher query
                self.connector.execute_query(query)
                # Log debug information, indicating the query was executed successfully
                logger.debug("Successfully executed cleanup query: %s", query)
            except Exception as e:
                # If an error occurs while executing the query, log the error information
                logger.error(f"Error executing cleanup query: {query} - {e}")

    def load_initial_data(self, json_file: str):
        """
        Loads initial data

        This function reads initial data from the specified JSON file and loads it into the cache for quick access
        It also writes character and relationship data to the Neo4j database

        Parameters:
        json_file (str): The path to the JSON file containing the initial data
        """

        # Open the JSON file and load the data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Cache initial relationships (for inheritance in chapter 0)
        self._initial_relationships = data.get('relationships', [])
        self._character_cache = {p['id']: p for p in data.get('characters', [])}
        self._relationship_cache = {
            f"{rel['from_id']}-{rel['to_id']}-{rel['type']}": rel
            for rel in data.get('relationships', [])
        }
        # debug：查看三个缓存
        # Initialize chapter number
        chapter = 0
        # Write characters and relationships to Neo4j
        self._update_characters(chapter)
        self._update_relationships(chapter)
        # Log the result of loading the data
        logger.info(f"✅ Initial data has been loaded into the knowledge graph, with {len(self._character_cache)} characters and {len(self._relationship_cache)} relationships")


    def _update_characters(self, chapter: int):
        """
        Updates character nodes in bulk

        This function is responsible for bulk updating the character data in the cache to the graph database, adding chapter-specific labels to each character

        Parameters:
        chapter (int): The current chapter number, used to add chapter-specific labels

        Returns:
        None
        """
        # If the character cache is empty, do not perform any operation
        if not self._character_cache:
            return

        # Cypher query statement for bulk updating character nodes and their properties, and adding chapter labels
        query = """
        UNWIND $characters AS character
        MERGE (p:Character {id: character.id})
        SET p += character.props
        WITH p
        CALL apoc.create.addLabels(p, ['Chapter' + $chapter]) YIELD node
        RETURN count(node) as count
        """

        # Prepare character data, organizing each character's properties and ID into the format required by the query
        characters_data = [{
            "id": pid,
            "props": {k: v for k, v in data.items() if k != 'id'}
        } for pid, data in self._character_cache.items()]

        # Execute the Cypher query to update character nodes and log the number of updated character nodes
        try:
            result = self.connector.execute_query(query, {
                "characters": characters_data,
                "chapter": chapter
            })
            logger.debug(f"Updated {result[0]['count']} character nodes")
        except Exception as e:
            logger.error(f"Failed to bulk update characters: {str(e)}")
            raise

    # Update relationship nodes
    def _update_relationships(self, chapter: int):
        """Relationship update: Copy relationships from the previous chapter to the current chapter, then override with the current chapter's relationships"""

        # 1. If it is chapter 0, use the initial relationships directly
        if chapter == 0:
            rels_to_update = list(self._relationship_cache.values())
        else:
            try:
                # 2. Query all relationships from the previous chapter
                # query = f"""
                #     MATCH (a:Character:Chapter{chapter - 1})-[r]->(b:Character:Chapter{chapter - 1})
                #     RETURN a.id as from_id, b.id as to_id, type(r) as type, properties(r) as props
                #     """
                query = f""" 
                    MATCH (a:Character:Chapter{chapter - 1})-[r]->(b:Character:Chapter{chapter - 1})
                    WHERE r.chapter = {chapter - 1}
                    RETURN a.id as from_id, b.id as to_id, type(r) as type, properties(r) as props
                    """
                inherited_rels = self.connector.execute_query(query) or []
                logger.info(f"Inherited {len(inherited_rels)} relationships from chapter {chapter - 1}")

                # 3. Build the list of relationships to update
                rels_to_update = []

                # First add all inherited relationships (copy to the current chapter)
                for rel in inherited_rels:
                    rel_data = {
                        'from_id': rel['from_id'],
                        'to_id': rel['to_id'],
                        'type': rel['type'],
                        **rel['props']
                    }
                    # Ensure the relationship is marked for the current chapter
                    rel_data['chapter'] = chapter
                    rels_to_update.append(rel_data)

                print("rels_to_update:", rels_to_update)


                # Override inherited relationships with the current chapter's relationships
                # print(self._relationship_cache.values())
                for new_rel in self._relationship_cache.values():
                    # Ensure the new relationship has the correct chapter mark
                    new_rel['chapter'] = chapter
                    # print("new_rel:",new_rel)

                    # Check if a relationship with the same from_id/to_id already exists (regardless of type)
                    found = False
                    # print("rels_to_update:",rels_to_update)
                    for i, existing_rel in enumerate(rels_to_update):
                        # print(i)
                        # print(existing_rel)
                        if (existing_rel['from_id'] == new_rel['from_id'] and
                                existing_rel['to_id'] == new_rel['to_id']):
                            # Override the existing relationship (replace the relationship in the same direction)
                            rels_to_update[i] = new_rel
                            print("rels_to_update:",rels_to_update)
                            found = True
                            logger.info(
                                f"Replaced relationship: {new_rel['from_id']}->{new_rel['to_id']} ({existing_rel['type']} -> {new_rel['type']})")
                            break

                    if not found:
                        # If it is a brand new relationship, add it to the list
                        rels_to_update.append(new_rel)
                        logger.info(f"Added new relationship: {new_rel['from_id']}->{new_rel['to_id']} ({new_rel['type']})")

                print("rels_to_update:", rels_to_update)

            except Exception as e:
                logger.error(f"Relationship update failed: {str(e)}")
                return

        # 4. Bulk update relationships to the current chapter
        query = f"""
            UNWIND $rels AS rel_data
            MATCH (a:Character:Chapter{chapter} {{id: rel_data.from_id}})
            MATCH (b:Character:Chapter{chapter} {{id: rel_data.to_id}})
            CALL apoc.merge.relationship(
                a,
                rel_data.type,
                {{  // Matching conditions: relationship type, chapter, from_id, to_id
                    chapter: $chapter,
                    from_id: rel_data.from_id,
                    to_id: rel_data.to_id
                }},
                {{  // Set these properties if a match is found
                    intensity: rel_data.intensity,
                    awareness: COALESCE(rel_data.awareness, 'Unknown'),
                    new_detail: COALESCE(rel_data.new_detail, ''),
                    reason: COALESCE(rel_data.reason, ''),
                    chapter: $chapter
                }},
                b,
                {{  // Set these properties if no match is found, for creating the relationship
                    intensity: rel_data.intensity,
                    awareness: COALESCE(rel_data.awareness, 'Unknown'),
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
            # Prepare relationship data
            rels_data = []
            for r in rels_to_update:
                rel_data = {
                    "from_id": r["from_id"],
                    "to_id": r["to_id"],
                    "type": r["type"],
                    "intensity": r.get("intensity", 3),
                    "awareness": r.get("awareness", "Unknown"),
                    "new_detail": r.get("new_detail", ""),
                    "reason": r.get("reason", "")
                }
                rels_data.append(rel_data)
                print("rels_data:",rels_data)

            # Use string replacement to handle chapter labels
            query = query.replace(":Chapter$chapter", f":Chapter{chapter}")
            print("query:", query)

            result = self.connector.execute_query(query, {
                "rels": rels_data,
                "chapter": chapter
            })
            print("result:",result)
            logger.info(f"Updated {result[0]['count']} relationships to chapter {chapter}")
        except Exception as e:
            logger.error(f"Relationship update failed: {str(e)}")

    def cleanup_duplicate_relationships(self):
        """Cleans up all duplicate relationships in the database"""
        query = """
        MATCH (a:Character)-[r]->(b:Character)      
        WITH a, b, type(r) as relType, r.chapter as chapter, collect(r) as rels
        WHERE size(rels) > 1
        UNWIND rels[1..] AS duplicateRel
        DELETE duplicateRel
        RETURN count(duplicateRel) as deletedCount
        """
        # The purpose of the above query is to find all duplicate relationships and delete the extras, retaining only one
        try:
            result = self.connector.execute_query(query)
            logger.info(f"Cleaned up {result[0]['deletedCount']} duplicate relationships")
        except Exception as e:
            logger.error(f"Failed to clean up duplicate relationships: {str(e)}")

    def check_chapter_relationships(self, chapter: int, show_all: bool = False):
        """Checks the relationship status of characters in a specified chapter, detecting duplicate relationships

        Args:
            chapter: The chapter number to check
            show_all: Whether to display all relationships (defaults to showing only problematic relationships)

        Returns:
            list: List of query results
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

            print(f"\n=== Chapter {chapter} Relationship Check ===")
            print(f"Found {len(results)} relationship records in total")

            duplicate_count = 0
            normal_count = 0

            for result in results:
                count = result['relationship_count']
                if count > 1:
                    duplicate_count += 1
                    print(
                        f"⚠️  Duplicate relationship: {result['from_id']}->{result['to_id']} "
                        f"({result['relationship_type']}) - Count: {count}"
                    )
                elif show_all:
                    normal_count += 1
                    print(
                        f"✅ Normal relationship: {result['from_id']}->{result['to_id']} "
                        f"({result['relationship_type']}) - Intensity: {result['intensity']}"
                    )

            # Statistics
            print(f"\n📊 Statistics: {duplicate_count} duplicate relationships, {len(results) - duplicate_count} normal relationships")

            if duplicate_count > 0:
                print(f"🔍 Suggestion: Consider using MERGE or checking relationship creation logic")

            return results

        except Exception as e:
            print(f"❌ Query execution failed: {str(e)}")
            return []

    def create_scene(self, chapter: int, **properties):
        """
        Creates/updates a scene node

        This function is used to create or update a scene node in a specific chapter. It requires the 'id' field to be included in the provided properties,
        to ensure the uniqueness of the scene. Other scene properties such as 'name', 'place', 'time_period', 'pov_character', and 'owner' can be specified
        through the properties parameter. If these properties are not specified, they will use default values.

        Parameters:
        - chapter (int): The chapter number to which the scene belongs
        - properties (dict): A dictionary containing scene properties, must include the 'id' key

        Returns:
        - result: The result of creating or updating the scene node

        Exceptions:
        - ValueError: If the 'id' property is not included in properties, this exception will be raised
        """
        # Check if the 'id' property is included in properties, raise ValueError if not
        if "id" not in properties:
            raise ValueError("Creating a Scene node requires an id property")

        # Define default scene properties, these will be used if not provided in properties
        default_props = {
            "name": None,
            "place": None,
            "time_period": "UNSPECIFIED",
            "pov_character": None,
            "owner": None
        }
        # Prepare scene properties, merging default properties with user-provided properties
        props = self._prepare_properties(properties, default_props)

        # Construct Cypher query for creating or updating the scene node
        query = f"""
        MERGE (s:Scene {{id: $id}})
        SET s:Chapter{chapter}, 
            s += $props
        RETURN s
        """
        try:
            # Execute the Cypher query to create or update the scene node and return the result
            result = self.connector.execute_query(query, {"id": props["id"], "props": props})
            # Log the result of creating or updating the scene node
            logger.debug("Created scene %s result: %s", props.get("name", props["id"]), result)
            return result
        except Exception as e:
            # If an exception occurs during query execution, log the error and re-raise the exception
            logger.error(f"Failed to create scene node: {e}")
            raise

    def create_event(self, chapter: int, **properties):
        """
        Creates an event node and associates it with a scene

        This method is primarily used to create an event node in a specific chapter and set it up based on the provided properties
        Additionally, if the event is associated with a scene or participants, it will create the corresponding relationships

        Parameters:
        - chapter (int): The chapter number to which the event belongs
        - properties (dict): The properties of the event, must include 'id', optionally including other properties such as 'name', 'details', 'order', 'emotional_impact', 'consequences', 'participants', 'scene_id', etc

        Exceptions:
        If 'id' is not included in the properties, a ValueError will be raised

        Returns:
        None
        """
        # Check if the required 'id' property is provided
        if "id" not in properties:
            raise ValueError("Creating an Event node requires an id property")

        # Define default property values for the event
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

        # Process emotional_impact, convert to JSON string if it is a dictionary
        if "emotional_impact" in properties and isinstance(properties["emotional_impact"], dict):
            properties["emotional_impact"] = json.dumps(properties["emotional_impact"], ensure_ascii=False)

        # Merge default properties with provided properties, ensuring all properties are defined
        props = self._prepare_properties(properties, default_props)

        # Create Cypher query for the event node
        query = f"""
        MERGE (e:Event {{id: $id}})
        SET e:Chapter{chapter}, 
            e += $props
        RETURN e
        """

        # Execute the query and handle exceptions
        try:
            result = self.connector.execute_query(query, {"id": props["id"], "props": props})
            logger.debug("Created event %s result: %s", props.get("name", props["id"]), result)
        except Exception as e:
            logger.error(f"Failed to create event node: {e}")
            raise

        # If there are participants, create participation relationships with the event
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
                logger.error(f"Failed to create participation relationship: {participant} -> {props['id']} - {e}")

        # If there is a scene_id, associate the event with the scene
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
                logger.error(f"Failed to associate scene: {props['id']} -> {props['scene_id']} - {e}")

    def process_chapter(self, json_file: str):
        """
        Processes the JSON data for a specified chapter, updates the cache and the Neo4j database.
        Processes files stored in the story_data/chapters/ directory and stores them in Neo4j
        This function first reads and parses the given JSON file, then updates the internal cache
        including the character and relationship caches based on the data in the file.
        Subsequently, it calls the appropriate processing functions for scenes and events,
        and finally updates the information in the Neo4j database.

        Parameters:
        json_file: str - The path to the JSON file containing chapter data.
        """

        # Read the JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded JSON data: {data}")

        # Get the chapter number
        chapter = data['chapter']
        logger.info(f"Starting to process data for chapter {chapter}...")

        # Clean up any existing duplicate relationships
        self.cleanup_duplicate_relationships()

        # Clear the current chapter's relationship cache
        self._relationship_cache = {}  # Completely clear the relationship cache

        # Update character cache
        updated_characters = set()  # Still stores character IDs
        for character in data.get('characters', []):
            character_id = character['id']
            if character_id in self._character_cache:
                # Merge and update properties
                self._character_cache[character_id].update(character)
                updated_characters.add(character_id)
            else:
                # Add new character
                self._character_cache[character_id] = character
                updated_characters.add(character_id)

        # Update relationship cache
        updated_rels = set()
        for rel in data.get('relationships', []):
            rel_key = f"{rel['from_id']}-{rel['to_id']}-{rel['type']}"  # Get the unique key for the relationship
            if rel_key in self._relationship_cache:
                # Update existing relationship
                self._relationship_cache[rel_key].update(rel)
            else:
                # Add new relationship
                self._relationship_cache[rel_key] = rel
            updated_rels.add(rel_key)

        # Process scenes and events
        for scene in data.get('scenes', []):
            self.create_scene(chapter, **scene)
        for event in data.get('events', []):
            self.create_event(chapter, **event)

        # Update Neo4j
        self._update_characters(chapter)
        self._update_relationships(chapter)

        logger.info(f"✅ Chapter {chapter} processing completed, updated {len(updated_characters)} characters and {len(updated_rels)} relationships")

    def get_character_profile(self, character_id: str, chapter: int):
        """
        Queries the complete profile of a character

        This function is used to query the complete profile information of a character based on the given character ID and chapter number.
        The profile includes the following:
        - Basic information (e.g., name, gender, age, etc.)
        - Relationship network (only returns relationships where the current character points to others)
        - Participated events (event name, scene, emotional impact, etc.)

        Parameters:
        - character_id (str): The unique identifier of the character to query
        - chapter (int): The chapter number, indicating in which chapter to query the character's information

        Returns:
        - dict: A dictionary containing the character's basic information, relationships, and participated events. If the character is not found, returns {"error": "Character not found"}.
        """
        # 1. Query basic information
        query = f"""
                MATCH (p:Character:Chapter{chapter} {{id: $character_id}})
                RETURN p {{.*}} as properties
                """
        character_info = self.connector.execute_query(query, {"character_id": character_id})

        if not character_info:
            return {"error": "Character not found"}

        # 2. Fix relationship query - Add parameterized query
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
            "chapter": chapter  # Add chapter parameter
        }) or []
        print("relationships:",relationships)

        # 3. Query events participated by the character
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

        # Emotional impact processing logic
        for event in events:
            if event["emotional_impact"]:
                try:
                    emotions = json.loads(event["emotional_impact"])
                    event["emotional_impact"] = emotions.get(character_id, "No record")
                except (json.JSONDecodeError, AttributeError):
                    event["emotional_impact"] = "Data format error"
            else:
                event["emotional_impact"] = "No record"

        return {
            "properties": character_info[0]['properties'],
            "relationships": [r["relationship"] for r in relationships],
            "events": events
        }

    def save_character_memories_kg(self, chapter: int, base_path: str = None):
        """
        Saves the memories of all characters to JSON files

        Parameters:
            chapter (int): Chapter number
            base_path (str): Optional custom base path
        """
        try:
            # Determine the base path
            if base_path is None:
                # Calculate the project root directory from the current file's directory
                current_dir = Path(__file__).parent
                # Correctly calculate the project root directory (adjust levels based on actual directory structure)
                project_root = current_dir.parent.parent.parent  # Assuming structure: project_root/Resource/tools/kg_builder.py
                # Set the default character memory storage directory
                base_path = project_root / "Resource" / "memory_Eng" / "character"
            else:
                # Handle custom path (supports string or Path object)
                base_path = Path(base_path)  # Ensure conversion to Path object

            # Create chapter memory folder (ensure the base path is correct)
            chapter_dir = base_path / f"chapter_{chapter}_memories"
            chapter_dir.mkdir(parents=True, exist_ok=True)

            # Get all character IDs for this chapter
            character_ids = self.get_chapter_character_ids(chapter)

            formatted_memory = {}
            # Save memories for each character
            for character_id in character_ids:
                memory = self.get_character_profile(character_id, chapter)

                # Ensure memory format is consistent with MemoryAgent
                formatted_memory = {
                    "chapter": chapter,
                    "properties": memory["properties"],
                    "relationships": memory["relationships"],
                    "events": memory["events"]
                }

                # Build the memory file path
                memory_file = chapter_dir / f"{character_id}_memory.json"

                # Save the JSON file
                with open(memory_file, 'w', encoding='utf-8') as f:
                    json.dump(formatted_memory, f, ensure_ascii=False, indent=2)

                logger.info(f"✅ Saved memory for character {character_id} to {memory_file}")

            return formatted_memory

        except Exception as e:
            logger.error(f"Failed to save character memories: {str(e)}")
            raise  # Re-raise the exception to let the caller handle it

    def get_chapter_character_ids(self, chapter: int) -> list:
        """
        Gets all character IDs for a specified chapter

        Parameters:
            chapter (int): Chapter number

        Returns:
            list: List of character IDs
        """
        query = f"""
        MATCH (p:Character:Chapter{chapter})
        RETURN p.id as character_id
        """
        try:
            result = self.connector.execute_query(query)
            return [record['character_id'] for record in result]
        except Exception as e:
            logger.error(f"Failed to get chapter character IDs: {e}")
            return []


# if __name__ == "__main__":
#     # Test complete functionality
#     test_character_profile("initial_data.json", "chapter_data.json", "p1")

# if __name__ == "__main__":
#     connector = Neo4jConnector()
#     builder = KnowledgeGraphBuilder(connector)
#     builder.clear_all_data()  # Clear first
#     builder.load_initial_data("/Users/sylvia/anaconda_projects/PythonProject/CreAgentive/Resource/memory/story_plan/initial_data.json")  # Then load
#
#     # Query initial data
#     result = connector.execute_query("MATCH (n:Chapter0) RETURN count(n) AS count")
#     print("Chapter0 node count:", result[0]["count"])
#
#     connector.close()
