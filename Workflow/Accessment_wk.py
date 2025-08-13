import os
import re
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage

from Resource.llmclient import LLMClientManager
from Resource.template.story_accessment_prompt.accessment_prompt_in_Chinese import LOCAL_PROMPT, GLOBAL_PROMPT, get_local_prompt ,get_global_prompt
llm_client = LLMClientManager().get_client("deepseek-v3")


class AccessmentWorkflow :
	def __init__(self, llm_client) :
		"""
		arg:
		llm_client: LLMClient instance used for generating text and evaluating stories.
		# config: Configuration dictionary containing parameters for the workflow.
		"""
		self.llm_client = llm_client
		# self.config = config
		self.global_features = []  # 用于存储全书的表面特征
		self.local_scores = {  # 用于存储每一章的局部评分
			"相关性" : [],
			"连贯性" : [],
			"共情性" : [],
			"惊喜性" : [],
			"创造力" : [],
			"复杂性" : [],
			"沉浸性" : []
		}
		self.global_scores = {  # 用于存储的全局评分
			"相关性" : [],
			"连贯性" : [],
			"共情性" : [],
			"惊喜性" : [],
			"创造力" : [],
			"复杂性" : [],
			"沉浸性" : []
		}
		self.object_condition = ""  # 用于存储当前世界的客观条件
		self.chapter_words_count = []  # 用于存储每一章的字数统计

	def __initialize_agent(self) :
		"""
		Initialize the workflow by setting up necessary components.
		This method can be extended to include more initialization logic if needed.
		"""
		# 定义两个智能体，第一个是局部评价者
		local_agent = AssistantAgent(
			name = "local_accessment_agent",
			description = "一个以章为单位对小说进行局部评分并且总结该章节的表面特征的Agent",
			model_client = llm_client,
			system_message = LOCAL_PROMPT,
		)

		# 创建剧本写作Agent
		global_writer = AssistantAgent(
			name = "global_accessment_agent",
			description = "一个以全书为单位对小说进行全局评分的Agent",
			model_client = llm_client,
			system_message = GLOBAL_PROMPT,
		)
		return {"local" : local_agent, "global" : global_writer}

	def __initialize_chapters(self,folder_path) :
		"""
		读取指定文件夹中的章节文件，按文件名中的序号排序后返回内容列表
		:param folder_path: 文件夹路径
		:return: 按顺序排列的章节内容列表
		"""
		chapter_files = []

		# 遍历文件夹，收集文件名和路径
		for file_name in os.listdir(folder_path) :
			match = re.search(r'chapter_(\d+)_novel\.txt', file_name)
			if match :
				chapter_num = int(match.group(1))
				chapter_files.append((chapter_num, os.path.join(folder_path, file_name)))

		# 按章节号排序
		chapter_files.sort(key = lambda x : x[0])

		# 读取文件内容
		chapters_content = []
		for _, file_path in chapter_files :
			with open(file_path, 'r', encoding = 'utf-8') as f :
				chapters_content.append(f.read())

		return chapters_content

	# 这个函数是要将全局特征处理成规范的字符串形式作为输入给全局智能体
	def __process_global_features(self) :
		response_string = ""
		index = 0  # 用来表示每一章的内容的
		if not self.global_features :  # 如果全局特征列表为空，返回空字符串
			return response_string
		for feature in self.global_features :  # 我的global_features是一个列表，其中的每一个元素都是一个字符串
			index += 1
			response_string += f"第{index}章的情节：{feature}\n\n"

		return response_string

	# 定义一个能够解析大模型输出内容的函数
	def __parse_response_of_localAgent(self, response) -> tuple | None :
		"""
		这是一个解析大模型输出内容的函数。
		模型的输入是大模型的输入，现在我要解析大模型的输出内容。
		返回的内容有两个：
		1. 局部评分（local_scores）：一个字典，包含各个局部评分指标的分数。
		2. 表面特征（features）：一个字典，包含该章节的表面特征信息。
		"""
		local_scores = {}
		features = {}
		# 用正则匹配最外层的大括号 {} 中的内容
		match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
		if not match :
			# 2. 如果没有找到```json```，则直接匹配最外层花括号中的JSON
			match = re.search(r"(\{.*\})", response, re.DOTALL)

		if not match :
			raise ValueError("未找到有效的JSON内容")

		if not match :
			raise ValueError("未找到有效的 JSON 内容")
		json_str = match.group(1).strip()
		try :
			response_json = json.loads(json_str)  # 将大模型的输出内容转换为JSON格式
			local_scores = response_json.get("局部评分", {})  # 获取局部评分
			features = response_json.get("表面特征", {})  # 获取表面特征
		except json.JSONDecodeError as e :  # 如果解析JSON失败，打印错误信息
			print(f"JSON解析错误: {e}\n" + "输出内容不是json格式：", response)
			return None, None
		return local_scores, features

	# 现在要一个能够解析global_agent的输出内容的函数
	def __parse_response_of_globalAgent(self, response) -> dict | None :
		"""
		解析全局智能体的输出内容。
		返回的内容是一个字典，包含全局评分指标的分数。
		"""
		# 先提取最外层的大括号 {} 中的内容
		match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
		if not match :
			# 2. 如果没有找到```json```，则直接匹配最外层花括号中的JSON
			match = re.search(r"(\{.*\})", response, re.DOTALL)

		if not match :
			raise ValueError("未找到有效的JSON内容")

		if not match :
			raise ValueError("未找到有效的 JSON 内容")
		json_str = match.group(1).strip()

		try :
			response_json = json.loads(json_str)  # 将大模型的输出内容转换为JSON格式
			global_scores = response_json.get("全局评分", {})  # 获取全局评分
			return global_scores
		except json.JSONDecodeError as e :  # 如果解析JSON失败，打印错误信息
			print(f"全局评分解析错误: {e}\n输出内容不是json格式：", response)
			return None

	# 这个函数的作用是将大模型的输出内容解析成一个字典，然后将局部评分存入成员变量local_scores中
	def __update_local_scores(self, local_scores) :
		"""
		更新局部评分到成员变量 local_scores 中。
		:param local_scores: 包含各个局部评分指标的分数字典。
		"""
		for key in self.local_scores.keys() : # 获取局部评分，如果没有则报错给用户说大模型没有评估这个指标
			if key in local_scores :
				self.local_scores[key].append(local_scores[key])
			else :
				print(f"大模型没有评估{key}指标，请检查提示词是否正确。")
				self.local_scores[key].append(0)

	# 这个函数用于更新情节概要和当前世界客观条件
	def __update_global_features(self, features) :
		"""
		更新全局特征，包括情节概要和当前世界客观条件。
		:param features: 包含情节概要和当前世界客观条件的字典。
		"""
		if "情节概要" in features :
			self.global_features.append(features["情节概要"])
		else :
			self.global_features.append("")
			print(f"大模型没有提取到情节概要，请检查提示词是否正确。")
		if "当前世界客观条件" in features :
			self.object_condition = features["当前世界客观条件"]
		else :
			self.object_condition = ""
			print(f"大模型没有提取到当前世界客观条件，请检查提示词是否正确。")

	# 定义一个能够给文章计数的函数，输入是每一章节的内容,数据类型是一个字符串，输出是一个整数，表示该章节的字数,然后存入全局变量中
	def __count_words(self, chapter_content) :
		"""
		计算章节内容的字数，并将结果存入成员变量 chapter_words_count 中。
		:param chapter_content: 章节内容字符串。
		:return: 章节内容的字数。
		要求中英文都能计数
		"""
		# 使用正则表达式匹配所有非空白字符
		word_count = len(re.findall(r'\S', chapter_content))
		self.chapter_words_count.append(word_count)
		return word_count  # 返回章节内容的字数

	# 现在要定义一个异步的run函数，来执行评估的流程
	async def run(self, *,chapters = r"C:\Users\pcw\Desktop\Recent_files\Agentnovel\CreAgentive\Resource\story"):
		# 这里的chapters传入的是一个本地路径，在路径里面有10个后缀为.txt的文件！！要将这10个文件的内容进行解析，然后传入一个列表中
		"""
		进行评估的开始函数，其中的参数chapters示例为：
		返回的内容是一个字典，包含全局评分和局部评分的平均值。
		"""
		agents = self.__initialize_agent()
		local_agent = agents["local"]
		global_agent = agents["global"]
		# 这里的给局部智能体输入是之前的章节大概以及当前章节的内容,现在要将路径中的章节内容转换成列表存储起来
		chapters_list = self.__initialize_chapters(chapters)  # 读取指定文件夹中的章节内容
		for chapter in chapters_list :
			# 先统计每一章的字数
			word_count = self.__count_words(chapter)
			print(f"第{len(self.global_features) + 1}章的字数：", word_count)
			input_message = get_local_prompt(prev_plot = self.__process_global_features(),
				object_condition = self.object_condition, next_content = chapter)
			response_local = await local_agent.run(
				task = input_message
			)
			await local_agent.model_context.clear()
			if response_local :  # 这里是判断response是否成功
				# 解析大模型的输出内容
				content = response_local.messages[-1].content  # 获取大模型的输出内容
				local_scores, features = self.__parse_response_of_localAgent(content)
				if local_scores is None or features is None :
					print("解析大模型输出内容失败，跳过当前章节。需要你修改提示词，确保起结构化输出")
					continue
				# 更新局部评分到成员变量
				self.__update_local_scores(local_scores)
				# 更新全局特征到成员变量
				self.__update_global_features(features)
				# 输出大模型的输出内容
				print(f"第{len(self.global_features)}章的局部评分：", local_scores)
				print(f"第{len(self.global_features)}章的表面特征：", features)

		# 计算局部指标的平均值
		local_scores = {key: sum(values) / len(values) if values else 0 for key, values in self.local_scores.items()}
		print("所有章节的局部平均评分：", local_scores)
		# 现在需要计算全局评分
		global_plot = self.__process_global_features()
		response_global = await global_agent.run(
			task = get_global_prompt(global_features = get_global_prompt(global_features=global_plot))
		)
		# 现在要解析大模型的输出内容为json格式
		if response_global :
			global_scores = self.__parse_response_of_globalAgent(response_global.messages[-1].content)
			if global_scores is None :
				print("解析全局评分失败，请检查提示词是否正确。")
				return None
			# 更新全局评分到成员变量
			self.global_scores = global_scores
			print("全局评分：", global_scores)
		else :
			print("全局评分获取失败，请检查提示词是否正确。")
			return None

		# 计算综合评分，局部和全局权重都是0.5
		final_scores = {}
		for key in self.local_scores.keys() :
			final_scores[key] = (local_scores[key] + global_scores[key]) / 2
		# 要给final_scores添加一个所有key值的平均值的键值对
		final_scores["平均分"] = sum(final_scores.values()) / len(final_scores)
		# 最后小说的综合评分
		print("综合评分：", final_scores)
		# 返回小说的已有章节的总字数和平均每章的字数，输出比如说，小说10个章节字数共有...个，平均每一章生成字数...
		total_words = sum(self.chapter_words_count)
		print(f"小说{len(self.chapter_words_count)}个章节字数共有{total_words}个，平均每一章生成字数{total_words / len(self.chapter_words_count):.2f}")




