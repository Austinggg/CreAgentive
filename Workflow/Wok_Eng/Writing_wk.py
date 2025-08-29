import os
import json
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock
from Agent.Agent_Eng.WriteAgent import create_agents
from Resource.tools.extract_llm_content import extract_llm_content
from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import UnboundedChatCompletionContext
from Agent.Agent_Eng.MemoryAgent import MemoryAgent
from Resource.tools.read_json import read_json

import re


class WritingWorkflow:
    """
    Writing workflow class responsible for orchestrating agents
    to complete the full process from chapter analysis to final text generation.
    Core functions: process chapter JSON data, invoke agents for foreshadowing detection and memory recall,
    integrate data, and generate novel or script output.
    """

    def __init__(self, model_client):
        """
        Initialize workflow parameters.

        Args:
            model_client: Language model client (e.g., DeepSeek) used for agent invocation.
        """
        self.model_client = model_client
        self.chapters_dir = os.path.join("Resource", "memory", "story_plan")
        self.save_dir = os.path.join("Resource", "story")
        self.current_chapter = 0
        self.chapter_count = 0
        self.memory_agent = MemoryAgent()

        # Agent initialization flag
        self.agents_initialized = False

    def _create_agents(self):
        """
        Create and initialize all required agents.
        Agents:
        - diggerAgent: Foreshadowing detection agent
        - recallAgent: Memory recall agent
        - novel_writer: Novel writing agent
        - script_writer: Script writing agent
        """
        if self.agents_initialized:
            return  # Avoid re-initialization

        agents = create_agents(self.model_client)
        self.diggerAgent = agents["diggerAgent"]
        self.recallAgent = agents["recallAgent"]
        self.novel_writer = agents["novel_writer"]
        self.script_writer = agents["script_writer"]
        self.agents_initialized = True
        print("✅ All agents initialized successfully")

    def _validate_article_type(self, article_type):
        """
        Validate article type.

        Args:
            article_type (str): Type of output, supports "novel" or "script".

        Returns:
            str: Lowercase valid type.

        Raises:
            AssertionError: If type is invalid.
        """
        article_type = article_type.lower()
        assert article_type in ["novel", "script"], "Article type must be 'novel' or 'script'"
        return article_type

    def _load_current_chapter(self, current_chapter_file):
        """
        Load current chapter JSON data.

        Args:
            current_chapter_file (str): Chapter filename (with .json extension).

        Returns:
            dict: Chapter data dictionary, structured as in chapter1.json.
        """
        current_path = os.path.join(self.chapters_dir, current_chapter_file)
        print(f"📖 Loading chapter file: {current_path}")
        data = read_json(current_path)
        return data

    async def _need_recall_and_load(self, current_data):
        """
        Perform per-character memory recall retrieval.

        Args:
            current_data (dict): Current chapter data.

        Returns:
            tuple: (recall flag dict, list of recall events)
        """
        print("\n" + "=" * 50)
        print("🔍 Starting per-character memory recall process")

        characters = current_data.get("characters", [])
        all_recall_events = []

        for character in characters:
            char_id = character["id"]
            print(f"\n👤 Processing character: {character.get('name')} ({char_id})")

            prev_events = self.memory_agent.get_previous_chapters_events(
                character_id=char_id,
                current_chapter=current_data["chapter"]
            )
            print(f"prev_events: {prev_events}")
            print(f"Number of prev_events: {len(prev_events)}")

            if not prev_events:
                print(f"⚠️ No prior chapter events for character {character.get('name')}")
                continue

            input_data = {
                "current_character": character,
                "current_events": [
                    e for e in current_data.get("events", [])
                    if char_id in e.get("participants", [])
                ],
                "past_events": prev_events
            }
            print(f"input_data: {input_data}")

            recall_result = await self.recallAgent.a_run(task=input_data)
            await self.recallAgent.model_context.clear()
            raw_output = extract_llm_content(recall_result)
            print(f"raw_output: {raw_output}")

            try:
                recall_resp = json.loads(strip_markdown_codeblock(raw_output))
                if recall_resp.get("need_recall") == "Yes":
                    print(f"✅ Recall needed for {character.get('name')}:")
                    for pos in recall_resp.get("positions", []):
                        event_details = self.memory_agent.get_event_details(pos["id"])
                        if event_details:
                            event_details["related_character"] = char_id
                            event_details["recall_reason"] = pos["reason"]
                            all_recall_events.append(event_details)
            except Exception as e:
                print(f"❌ Failed to process recall for {character.get('name')}: {str(e)}")

        return {"need_recall": "Yes" if all_recall_events else "No"}, all_recall_events

    async def _need_dig_and_load(self, current_data):
        """
        Retrieve foreshadowing events from future chapters.

        Args:
            current_data (dict): Current chapter data.

        Returns:
            tuple: (dig flag dict, list of dig events)
        """
        print("\n" + "=" * 50)
        print("🔮 Starting foreshadowing event retrieval process")

        next_events = self.memory_agent.get_next_chapters_events(
            current_chapter=current_data["chapter"],
            end_chapter=self.chapter_count
        )
        print("next_events:", next_events)

        if not next_events:
            print("ℹ️ No future chapter events available for foreshadowing")
            return {"need_dig": "No"}, []

        input_data = {
            "current_chapter": current_data,
            "future_events": next_events
        }

        dig_result = await self.diggerAgent.a_run(task=input_data)
        await self.diggerAgent.model_context.clear()
        raw_output = extract_llm_content(dig_result)

        try:
            dig_resp = json.loads(strip_markdown_codeblock(raw_output))
            dig_events = []
            if dig_resp.get("need_dig") == "Yes":
                for pos in dig_resp.get("positions", []):
                    event_details = self.memory_agent.get_event_details(pos["id"])
                    if event_details:
                        dig_events.append(event_details)
            return dig_resp, dig_events
        except Exception as e:
            print(f"❌ Foreshadowing analysis failed: {str(e)}")
            return {"need_dig": "No"}, []

    async def _combine_plans(self, current_data, dig_events, recall_events):
        """
        Combine current chapter data with foreshadowing and recall events.

        Args:
            current_data (dict): Full current chapter data.
            dig_events (list): List of foreshadowing events from future chapters.
            recall_events (list): List of recall events from prior chapters.

        Returns:
            dict: Combined chapter data with added dig_events and recall_events.
        """
        print("\n" + "=" * 50)
        print("🧩 Starting full data integration")

        combined = json.loads(json.dumps(current_data))
        combined["dig_events"] = []
        combined["recall_events"] = []

        for event in dig_events or []:
            if isinstance(event, dict):
                event.setdefault("source_type", "dig")
                combined["dig_events"].append(event)

        for event in recall_events or []:
            if isinstance(event, dict):
                event.setdefault("source_type", "recall")
                combined["recall_events"].append(event)

        init_data = self._load_current_chapter("chapter_0.json")
        combined = {
            "title": init_data["title"],
            "background": init_data["background"],
            "init_relationships": init_data["relationships"],
            **current_data,
            "dig_events": dig_events or [],
            "recall_events": recall_events or []
        }

        self._print_integration_details(combined)
        return combined

    def _print_integration_details(self, data):
        """Print detailed integration report."""
        print("\n📊 Integration Details Report")
        print(f"=== Chapter {data.get('chapter', 'Unknown')} ===")

        print("\n📌 Initial Settings:")
        print(f"- Title: {len(data.get('title', ''))}")
        print(f"- Background: {len(data.get('background', ''))}")

        print("\n📌 Chapter Data:")
        print(f"- Characters: {len(data.get('characters', []))}")
        print(f"- Relationships: {len(data.get('relationships', []))}")
        print(f"- Scenes: {len(data.get('scenes', []))}")
        print(f"- Main Events: {len(data.get('events', []))}")

        print("\n🔮 Foreshadowing Events:")
        for event in data.get("dig_events", [])[:2]:
            print(json.dumps(event, indent=2, ensure_ascii=False))

        print("\n📜 Recall Events:")
        for event in data.get("recall_events", [])[:2]:
            print(json.dumps(event, indent=2, ensure_ascii=False))

        print("\n✅ Final Data Structure Validation:")
        required_fields = ["chapter", "characters", "events", "dig_events", "recall_events"]
        for field in required_fields:
            exists = "✔️" if field in data else "❌"
            print(f"{exists} {field}: {type(data.get(field))}")

    async def _write_and_save(self, combined_data, chapter_num, article_type):
        """
        Generate and save the chapter text.

        Args:
            combined_data (dict): Integrated chapter data.
            chapter_num (int): Chapter number.
            article_type (str): Output type ('novel' or 'script').

        Returns:
            str: Generated text content, or empty string on failure.
        """
        writer = self.novel_writer if article_type == "novel" else self.script_writer
        print(f"✍️ Generating Chapter {chapter_num} {article_type}...")

        try:
            write_result = await writer.a_run(task=combined_data)
            print("Writing agent call completed")
            await self.novel_writer.model_context.clear()
            await self.script_writer.model_context.clear()

            print("\n======================\n")
            print(f"✍️ Chapter {chapter_num} {article_type} generated")
            print(write_result)

            raw_output = extract_llm_content(write_result)
            print("\n💡 Raw output from writing agent:")
            print(raw_output)

            output_text = strip_markdown_codeblock(raw_output).strip()
            chapter_title = combined_data.get("chapter_title", f"Chapter {chapter_num}")
            output_text = f"{chapter_title}\n\n{output_text}"

            if not output_text or len(output_text) < 10:
                raise ValueError(
                    f"Invalid generated content "
                    f"| Raw length: {len(raw_output)} "
                    f"| Cleaned length: {len(output_text)}"
                )

            ext = ".txt" if article_type == "novel" else ".md"
            filename = f"chapter_{chapter_num}_{article_type}{ext}"
            self._save_text(output_text, filename)
            print(f"📦 Saved to: {os.path.join(self.save_dir, filename)}")

            return output_text

        except Exception as e:
            print(f"⚠️ Writing failed: {str(e)}")
            debug_info = (
                f"Error: {str(e)}\n"
                f"Result type: {type(write_result)}\n"
                f"Result content: {str(write_result)}\n"
                f"extract_llm_content output: {raw_output}\n"
                f"Stripped content: {output_text if 'output_text' in locals() else 'undefined'}"
            )
            self._save_text(debug_info, f"chapter_{chapter_num}_debug.txt")
            return ""

    def _save_text(self, content, filename):
        """
        Save text content to file.

        Args:
            content (str): Text content to save.
            filename (str): Target filename.
        """
        os.makedirs(self.save_dir, exist_ok=True)
        full_path = os.path.join(self.save_dir, filename)

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"📦 Saved to: {full_path}")

    async def run_single_chapter(self, chapter_file, article_type="novel"):
        """
        Process a single chapter end-to-end.

        Args:
            chapter_file (str): Chapter filename (e.g., 'chapter1.json').
            article_type (str): Output type ('novel' or 'script').

        Returns:
            str: Generated chapter text.
        """
        current_data = self._load_current_chapter(chapter_file)
        chapter_num = current_data.get("chapter", "unknown")

        dig_resp, dig_data = await self._need_dig_and_load(current_data)
        recall_resp, recall_data = await self._need_recall_and_load(current_data)

        print(dig_resp)
        print(dig_data)
        print(recall_resp)
        print(recall_data)

        combined_data = await self._combine_plans(current_data, dig_data, recall_data)
        print(combined_data)

        return await self._write_and_save(combined_data, chapter_num, article_type)

    async def run_all_chapters(self, article_type="novel"):
        """
        Process all chapters in order.

        Args:
            article_type (str): Output type ('novel' or 'script').
        """
        print(f"Checking directory: {self.chapters_dir}")
        print(f"Directory contents: {os.listdir(self.chapters_dir)}")

        all_files = [
            f for f in os.listdir(self.chapters_dir)
            if f.endswith('.json') and f != "chapter_0.json"
        ]

        all_files = sorted(all_files, key=lambda x: int(re.search(r'(\d+)', x).group(1)))
        self.chapter_count = len(all_files)

        print(f"📑 Found {len(all_files)} chapter files (skipping chapter_0.json), starting batch processing...")

        for i, chapter_file in enumerate(all_files, 1):
            self.current_chapter = i
            print(f"\n===== Processing Chapter {i}/{len(all_files)}: {chapter_file} =====")
            await self.run_single_chapter(chapter_file, article_type)

    async def run(self, article_type="novel"):
        """
        Launch the full writing workflow.

        Args:
            article_type (str): Output type ('novel' or 'script').
        """
        article_type = self._validate_article_type(article_type)
        self._create_agents()

        if self.novel_writer is None:
            raise ValueError("Novel writing agent not initialized properly")

        await self.run_all_chapters(article_type)
        print("\n🎉 All chapters processed successfully!")