import os
import re
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from Resource.llmclient import LLMClientManager
from Resource.template.story_accessment_prompt.accessment_prompt_in_Eng import LOCAL_PROMPT, GLOBAL_PROMPT, LOCAL_PROMPT_TEMPLATE , GLOBAL_PROMPT_TEMPLATE
llm_client = LLMClientManager().get_client("deepseek-v3")

class AccessmentWorkflow:
    def __init__(self, llm_client):
        """
        Args:
            llm_client: LLMClient instance used for generating text and evaluating stories.
        """
        self.llm_client = llm_client
        self.global_features = []  # Stores high-level plot summaries of all chapters
        self.local_scores = {  # Stores per-chapter evaluation scores
            "Relevance": [],
            "Coherence": [],
            "Empathy": [],
            "Surprise": [],
            "Creativity": [],
            "Complexity": [],
            "Immersion": []
        }
        # Stores overall book-level scores
        self.global_scores = {  # Stores overall book-level scores
            "Relevance": [],
            "Coherence": [],
            "Empathy": [],
            "Surprise": [],
            "Creativity": [],
            "Complexity": [],
            "Immersion": []
        }
        self.object_condition = ""  # Stores current objective world conditions
        self.chapter_word_count = []  # Stores word count for each chapter

    def __initialize_agents(self):
        """
        Initialize local and global assessment agents.
        """
        local_agent = AssistantAgent(
            name="local_assessment_agent",
            description="An agent that evaluates each chapter individually and summarizes surface features.",
            model_client=self.llm_client,
            system_message=LOCAL_PROMPT,
        )

        global_agent = AssistantAgent(
            name="global_assessment_agent",
            description="An agent that evaluates the book as a whole.",
            model_client=self.llm_client,
            system_message=GLOBAL_PROMPT,
        )
        return {"local": local_agent, "global": global_agent}

    def __load_chapters(self, folder_path):
        """
        Reads and returns chapter content from the specified folder, sorted by chapter number.
        :param folder_path: Path to the folder containing chapter text files.
        :return: List of chapter content strings.
        """

        chapter_files = []
        for file_name in os.listdir(folder_path):
            match = re.search(r'chapter_(\d+)_novel\.txt', file_name)
            if match:
                chapter_num = int(match.group(1))
                chapter_files.append((chapter_num, os.path.join(folder_path, file_name)))
        chapter_files.sort(key=lambda x: x[0])
        chapters_content = []
        for _, file_path in chapter_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                chapters_content.append(f.read())
        return chapters_content

    def __get_local_prompt(self,*, prev_plot, object_condition, next_content) :
        return LOCAL_PROMPT_TEMPLATE.format(
            prev_plot = prev_plot,
            object_condition = object_condition,
            next_content = next_content
        )

    def __get_global_prompt(self,*, global_features) :
        return GLOBAL_PROMPT_TEMPLATE.format(
            global_features = global_features
        )

    def __format_global_features(self):
        """
        Converts stored global features into a formatted string for the global agent.
        """
        if not self.global_features:
            return ""
        result = ""
        for idx, feature in enumerate(self.global_features, 1):
            result += f"Chapter {idx} plot: {feature}\n\n"
        return result

    def __parse_local_agent_response(self, response) -> tuple | None:
        """
        Parses the local agent's output.
        Returns:
            local_scores (dict): Per-chapter scores for each metric.
            features (dict): Extracted surface features of the chapter.
        """
        match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL) # 这段正则表达式用于匹配代码块中的JSON格式内容
        if not match:
            match = re.search(r"(\{.*\})", response, re.DOTALL) # 这段代码是用于匹配没有代码块的JSON格式内容

        if not match:
            raise ValueError("No valid JSON found in local agent response.")

        json_str = match.group(1).strip()
        try:
            data = json.loads(json_str)
            local_scores = data.get("Partial Scores", {})
            features = data.get("Surface Features", {})
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}\nOutput was not valid JSON: {response}")
            return None, None
        return local_scores, features

    def __parse_global_agent_response(self, response) -> dict | None:
        """
        Parses the global agent's output and returns a dict of overall book scores.
        """
        match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
        if not match:
            match = re.search(r"(\{.*\})", response, re.DOTALL)

        if not match:
            raise ValueError("No valid JSON found in global agent response.")

        json_str = match.group(1).strip()
        try:
            data = json.loads(json_str)
            return data.get("Global Scores", {})
        except json.JSONDecodeError as e:
            print(f"Global scores parsing error: {e}\nOutput was not valid JSON: {response}")
            return None

    def __update_local_scores(self, local_scores):
        """
        Updates the per-chapter score dictionary with new scores.
        """
        for key in self.local_scores.keys():
            if key in local_scores:
                self.local_scores[key].append(local_scores[key])
            else:
                print(f"Local agent did not evaluate the '{key}' metric.")
                self.local_scores[key].append(0)

    def __update_global_features(self, features):
        """
        Updates global plot summaries and objective world conditions.
        """
        if "Plot Summary" in features:
            self.global_features.append(features["Plot Summary"])
        else:
            self.global_features.append("")
            print("No plot summary found in features.")

        if "Current Objective Conditions" in features:
            self.object_condition = features["Current Objective Conditions"]
        else:
            self.object_condition = ""
            print("No current world condition found in features.")

    def __count_words(self, chapter_content):
        """
        Counts all non-whitespace characters (supports both English and Chinese).
        """
        word_count = len(re.findall(r'\S', chapter_content))
        self.chapter_word_count.append(word_count)
        return word_count

    async def run(self, *, chapters=r"C:\path\to\chapters"):
        """
        Runs the assessment workflow.
        """
        agents = self.__initialize_agents()
        local_agent = agents["local"]
        global_agent = agents["global"]

        chapters_list = self.__load_chapters(chapters)

        for chapter in chapters_list:
            word_count = self.__count_words(chapter)
            print(f"Chapter {len(self.global_features) + 1} word count: {word_count}")
            input_message = self.__get_local_prompt(
                prev_plot=self.__format_global_features(),
                object_condition=self.object_condition,
                next_content=chapter
            )

            response_local = await local_agent.run(task=input_message)
            await local_agent.model_context.clear()

            if response_local:
                content = response_local.messages[-1].content
                local_scores, features = self.__parse_local_agent_response(content)
                if local_scores is None or features is None:
                    print("Failed to parse local agent output — ensure structured JSON output.")
                    continue

                self.__update_local_scores(local_scores)
                self.__update_global_features(features)

                print(f"Chapter {len(self.global_features)} local scores: {local_scores}")
                print(f"Chapter {len(self.global_features)} surface features: {features}")

        # Calculate average local scores
        avg_local_scores = {
            key: sum(values) / len(values) if values else 0
            for key, values in self.local_scores.items()
        }
        print("Average local scores across all chapters:", avg_local_scores)

        # Get global scores
        global_plot = self.__format_global_features()
        response_global = await global_agent.run(
            task=self.__get_global_prompt(global_features=global_plot)
        )

        if response_global:
            global_scores = self.__parse_global_agent_response(
                response_global.messages[-1].content
            )
            if global_scores is None:
                print("Failed to parse global scores.")
                return None
            self.global_scores = global_scores
            print("Global scores:", global_scores)
        else:
            print("Global scoring failed.")
            return None

        # Final combined score (50% local + 50% global)
        final_scores = {
            key: (avg_local_scores[key] + self.global_scores[key]) / 2
            for key in self.local_scores.keys()
        }

        final_scores["Average"] = sum(final_scores.values()) / len(final_scores)

        print("Final combined scores:", final_scores)

        total_words = sum(self.chapter_word_count)
        print(
            f"Book has {len(self.chapter_word_count)} chapters, total word count: {total_words}, "
            f"average per chapter: {total_words / len(self.chapter_word_count):.2f}"
        )
