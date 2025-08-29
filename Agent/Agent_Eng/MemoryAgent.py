import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict
from Resource.tools.Eng.kg_builder import KnowledgeGraphBuilder
from Resource.tools.neo4j_connector import Neo4jConnector

# Set up logging
logging.basicConfig(level=logging.INFO)  # Set log level to INFO
logger = logging.getLogger(__name__)  # Get logger for current module


class MemoryAgent:
    """
    An intelligent agent that encapsulates novel chapter data processing,
    knowledge graph building, and character memory querying.
    """

    def __init__(self):
        self.connector = Neo4jConnector()  # Connect to Neo4j database
        self.builder = KnowledgeGraphBuilder(self.connector)  # Init builder
        self.current_chapter = 0  # Init current chapter number to 0
        print("MemoryAgent initialized")
        logger.info("MemoryAgent initialized")

    def clear_all_chapter_data(self):
        """
        Clear data for all chapters.

        Iterate chapter numbers 1 to 999 and call the graph builder
        to clear each chapter's data.
        """
        # Default max chapter is 999; adjust range as needed.
        for chapter in range(1, 1000):
            self.builder.clear_chapter_data(chapter)

    def load_initial_data(self, json_file: str):
        """
        Call the initial data loading method of KnowledgeGraphBuilder.

        Read initial data (characters and relationships) from the specified
        JSON file and load it into the knowledge graph as basic data
        for chapter 0.

        Parameters:
            json_file (str): Path to JSON file containing initial data
        """
        try:
            # Check if JSON file exists
            if not Path(json_file).exists():
                raise FileNotFoundError(
                    f"Initial data JSON file not found: {json_file}")

            self.builder.load_initial_data(json_file)

            # Log loading result
            logger.info(
                f"✅ Initial data loaded, "
                f"{len(self.builder._character_cache)} characters and "
                f"{len(self.builder._relationship_cache)} relationships")
            return True
        except Exception as e:
            logger.error(f"Failed to load initial data: {str(e)}")
            return False

    def load_chapter(self, json_path: str) -> bool:
        """
        Load and build chapter knowledge graph.

        Load chapter data from the specified JSON file and call the graph
        builder to import it into the Neo4j graph database.

        Parameters:
            json_path (str): Path to JSON file containing chapter data.

        Returns:
            bool: True if chapter knowledge graph is built successfully,
                  otherwise False.
        """
        try:
            # Check if JSON file exists
            if not Path(json_path).exists():
                raise FileNotFoundError(f"JSON file not found: {json_path}")

            # Open and read JSON file content
            with open(json_path, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
                self.current_chapter = chapter_data["chapter"]

            # Process chapter data (update Neo4j)
            self.builder.process_chapter(json_path)

            # If graph built successfully, log and return True
            logger.info(
                f"Successfully built knowledge graph for "
                f"Chapter {self.current_chapter}")
            return True
        except Exception as e:
            # Catch exceptions and log error messages
            logger.error(f"Failed to load chapter: {str(e)}")
            return False

    def get_event(self, event_id: str) -> Dict:
        """
        Get all properties of a specified event.

        Query the event node by event ID and return all its properties.

        Parameters:
            event_id (str): Event ID to query

        Returns:
            Dict: Dictionary containing all event properties;
                  returns error message if event does not exist
        """
        query = """
        MATCH (e:Event {id: $event_id})
        RETURN properties(e) as event_properties
        """
        params = {"event_id": event_id}

        try:
            result = self.connector.execute_query(query, params)
            if not result:
                return {"error": f"Event ID {event_id} does not exist"}

            event_properties = result[0]["event_properties"]
            logger.info(f"Successfully retrieved properties for event {event_id}")
            return event_properties

        except Exception as e:
            error_msg = f"Failed to get event properties: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_event_details(self, event_id: str) -> Dict:
        """
        Get details property content of a specified event.

        Query the event node by event ID and return its details property.

        Parameters:
            event_id (str): Event ID to query

        Returns:
            Dict: Dictionary containing the event's details property;
                  returns error message if event does not exist
                  or lacks details property
        """
        query = """
        MATCH (e:Event {id: $event_id})
        RETURN e.details as event_details
        """
        params = {"event_id": event_id}

        try:
            result = self.connector.execute_query(query, params)
            if not result:
                return {"error": f"Event ID {event_id} does not exist"}

            # Check if details property exists
            event_details = result[0].get("event_details")
            if event_details is None:
                return {"error": f"Event ID {event_id} has no details property"}

            logger.info(
                f"Successfully retrieved details property for event {event_id}")
            return {"details": event_details}

        except Exception as e:
            error_msg = f"Failed to get event details property: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_character_memory(self, character_id: str, chapter: int) -> Dict:
        """
        Get specified character's memory in a specific chapter.

        This function uses character_id and chapter parameters to call
        builder's get_character_profile method to obtain basic memory info
        for the character, processes and formats it, and returns an
        enhanced memory dictionary.

        Parameters:
            character_id (str): Character ID specifying which character's
                                memory to retrieve
            chapter (int): Chapter number specifying which chapter's
                           memory for the character

        Returns:
            Dict: Formatted character memory dictionary;
                  if error occurs, returns error message directly
        """

        # Call builder method to get character memory info
        memory = self.builder.get_character_profile(character_id, chapter)

        # Check if retrieved memory contains error info; if so, return directly
        if "error" in memory:
            return memory

        # Define the output format for memory read from knowledge graph,
        # i.e., enhanced memory format.
        # Enhanced format includes chapter, character properties,
        # relationships, and events.
        enhanced_memory = {
            "chapter": chapter,
            "characters": memory["properties"],
            "relationships": memory["relationships"],
            "events": memory["events"]
        }
        # Return enhanced memory
        return enhanced_memory

    def save_character_memories(self, chapter: int, base_path: str = None):
        """
        Find all character memories under the input chapter.

        Save all character memories under the input chapter to JSON files.

        Parameters:
            chapter (int): Chapter number
            base_path (str): Optional custom base path
        """
        try:
            # Use knowledge graph builder method to save memories
            self.builder.save_character_memories_kg(chapter, base_path)
            logger.info(f"Successfully saved character memories for Chapter {chapter}")
        except Exception as e:
            logger.error(f"Failed to save character memories: {str(e)}")
            raise

    def get_previous_chapters_events(self, character_id: str, current_chapter: int):
        """
        Get events from the previous five chapters from saved character memories.

        If current chapter <= 5, return all events from Chapter 1 to
        chapter before current.
        """
        previous_events = []

        # Limit number of events
        limit = 2

        # Determine query range
        start_chapter = max(1, current_chapter - 2)
        end_chapter = current_chapter - 1

        # Iterate each chapter in range
        for chapter in range(start_chapter, end_chapter + 1):
            try:
                # Get character memory for this chapter
                memory = self.get_character_memory(character_id, chapter)
                if memory and "events" in memory:
                    # Add chapter info to each event
                    for event in memory["events"]:
                        event["chapter_num"] = chapter
                        event["chapter_label"] = f"Chapter{chapter}"
                    previous_events.extend(memory["events"])
            except Exception as e:
                logger.error(f"Failed to get memory for Chapter {chapter}: {str(e)}")

        # Sort by chapter and event order
        previous_events.sort(
            key=lambda x: (x["chapter_num"], x.get("event_order", 0)))

        # If limit is set, return limited number of events
        if limit is not None:
            previous_events = previous_events[:limit]

        return previous_events

    def get_next_chapters_events(self, current_chapter: int, end_chapter: int):
        """
        Get all events from up to 5 chapters after current chapter
        (enhanced compatibility version).
        """
        # Limit number of events
        limit = 2

        if current_chapter >= end_chapter:
            return []

        # More robust query plan
        query = """
        MATCH (e:Event)
        // Extract all Chapter-prefixed labels
        WITH e, [label IN labels(e) WHERE label STARTS WITH 'Chapter'] AS chapter_labels
        WHERE size(chapter_labels) > 0
        // Extract numeric part (compatible with various Chapter label formats)
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
            logger.info(
                f"Query events after Chapter {current_chapter}: "
                f"conditions {params} returned {len(result)} items")

            # If limit is set, return limited number of events
            if limit is not None:
                result = result[:limit]

            return result
        except Exception as e:
            logger.error(f"Failed to query subsequent chapter events: {str(e)}")
            return []

    def close(self):
        """
        Close connection to Neo4j database.
        """
        self.connector.close()  # Close Neo4j database connection
        logger.info("Neo4j connection closed")  # Log connection closure info