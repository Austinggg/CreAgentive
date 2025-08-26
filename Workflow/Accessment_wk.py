import os
import re
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from collections import Counter
import numpy as np  # 用于标准差计算，如果环境中不可用，可用math.sqrt(sum((x - mean)**2 for x in lst) / (len(lst)-1)) 替换

from Resource.llmclient import LLMClientManager
from Resource.template.story_accessment_prompt.accessment_prompt_in_Chinese import LOCAL_PROMPT, GLOBAL_PROMPT ,LOCAL_PROMPT_TEMPLATE ,GLOBAL_PROMPT_TEMPLATE
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
		self.text_features = []  # 用于存储每一章的文字特征

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

	# 定义一个计算章节内容文字特征的函数__get_text_features，包含词汇多样性、句式复杂度等特征。该函数返回的内容包括
	def __get_text_features(self, chapter_content):
		"""
		计算章节内容的文字特征，包括词汇多样性和句式复杂度。
		该函数设计为支持中文和英文小说文本的分析。
		- 语言检测：通过计算文本中中文字符的比例来自动检测主要语言。如果中文字符比例 > 50%，则视为中文模式（以单个汉字作为“词”单位）；否则视为英文模式（以空格分隔的单词作为“词”单位）。
		- 词汇多样性：针对不同语言模式调整分词逻辑。英文使用正则匹配单词，中文使用单个汉字。
		- 句式复杂度：句子分割支持中英文标点。复合句和衔接词关键词列表包含中英文常用词。
		- 词性分布：由于标准库无NLP支持（如nltk或jieba），此部分未实现（返回占位符）。
		- 依赖：仅使用Python标准库（re, collections, numpy - 但numpy在工具环境中可用，如果不可用可移除std计算或用math代替）。
		:param chapter_content: 章节内容字符串。
		:return: 包含文字特征的字典。
		"""
		import re
		from collections import Counter
		import numpy as np  # 用于标准差计算，如果环境中不可用，可用math.sqrt(sum((x - mean)**2 for x in lst) / (len(lst)-1)) 替换

		features = {}

		# 1. 语言检测：计算中文字符比例
		chinese_chars = re.findall(r'[\u4e00-\u9fa5]', chapter_content)
		total_chars = len(re.sub(r'\s+', '', chapter_content))  # 总非空白字符数
		chinese_ratio = len(chinese_chars) / total_chars if total_chars > 0 else 0.0
		is_chinese = chinese_ratio > 0.5  # 如果 >50% 为中文字符，则视为中文模式

		# 2. 分词逻辑
		if is_chinese:
			# 中文模式：提取单个汉字作为“词”
			words = chinese_chars  # 已从上面提取
		else:
			# 英文模式：提取单词（忽略标点，转换为小写）
			words = re.findall(r'\b[a-zA-Z]+\b', chapter_content.lower())

		total_words = len(words)
		if total_words == 0:
			# 如果没有词，返回空特征
			return features

		# 3. 词汇多样性
		# 型例比（TTR）
		unique_words = set(words)
		ttr = len(unique_words) / total_words
		features['型例比'] = ttr

		# 修正TTR（滑动窗口，每1000词的TTR均值）
		window_size = 1000
		corrected_ttrs = []
		if total_words >= window_size:
			step = window_size // 2  # 步长为窗口一半，增加平滑
			for i in range(0, total_words - window_size + 1, step):
				window = words[i:i + window_size]
				window_ttr = len(set(window)) / len(window)
				corrected_ttrs.append(window_ttr)
			corrected_ttr = sum(corrected_ttrs) / len(corrected_ttrs) if corrected_ttrs else ttr
		else:
			corrected_ttr = ttr
		features['修正型例比'] = corrected_ttr

		# 词汇重复率：3-gram重复率（基于连续3个“词”）
		n = 3
		ngrams = [''.join(words[i:i + n]) for i in range(total_words - n + 1)]  # 对于英文，join会无空格；中文已无空格
		if ngrams:
			ngram_counter = Counter(ngrams)
			# 计算重复次数（每个ngram出现超过1次的额外计数）
			repeated_count = sum(count - 1 for count in ngram_counter.values() if count > 1)
			repeat_rate = repeated_count / len(ngrams) if len(ngrams) > 0 else 0.0
		else:
			repeat_rate = 0.0
		features['N-gram重复率'] = repeat_rate

		# 词频分布：高频词（出现>10次）占比，低频词（出现=1次）占比
		word_counter = Counter(words)
		high_freq_threshold = 10
		high_freq_count = sum(count for count in word_counter.values() if count > high_freq_threshold)
		high_freq_ratio = high_freq_count / total_words if total_words else 0.0
		low_freq_count = sum(1 for count in word_counter.values() if count == 1)
		low_freq_ratio = low_freq_count / len(unique_words) if unique_words else 0.0  # 低频词占比 = 唯一词中出现1次的比例
		features['高频词占比'] = high_freq_ratio
		features['低频词占比'] = low_freq_ratio

		# 词性分布：无法实现（需要NLP库如nltk for English 或 jieba for Chinese）
		features['词性分布'] = '未实现，需要NLP库'

		# 4. 句式复杂度
		# 分割句子（支持中英文标点）
		sentences = re.split(r'[.。!！?？;；:：]', chapter_content)
		sentences = [s.strip() for s in sentences if s.strip()]
		total_sentences = len(sentences)
		if total_sentences == 0:
			return features

		# 句子长度（按非空白字符数计算，通用中英）
		sent_lengths = [len(re.sub(r'\s+', '', s)) for s in sentences]  # 移除空格后计数

		# 平均句子长度
		avg_sentence_length = sum(sent_lengths) / total_sentences
		features['平均句子长度'] = avg_sentence_length

		# 句子长度标准差
		if total_sentences > 1:
			sentence_length_std = np.std(sent_lengths)
		else:
			sentence_length_std = 0.0
		features['句子长度标准差'] = sentence_length_std

		# 长句（>30字）、中句（10-30字）、短句（<10字）比例（字数通用中英，非空白字符）
		long_sentence_count = sum(1 for length in sent_lengths if length > 30)
		medium_sentence_count = sum(1 for length in sent_lengths if 10 <= length <= 30)
		short_sentence_count = sum(1 for length in sent_lengths if length < 10)
		features['长句比例'] = long_sentence_count / total_sentences if total_sentences else 0.0
		features['中句比例'] = medium_sentence_count / total_sentences if total_sentences else 0.0
		features['短句比例'] = short_sentence_count / total_sentences if total_sentences else 0.0

		# 复合句比例：含常见从句或连词（支持中英文关键词）
		compound_keywords = [
			# 中文
			'因为', '所以', '但是', '而且', '虽然', '然而', '如果', '并且', '不过', '即使',
			# 英文 (小写匹配，假设文本lower())
			'because', 'so', 'but', 'and', 'although', 'however', 'if', 'also', 'though', 'even'
		]
		lower_content = chapter_content.lower()  # 为英文匹配转小写
		compound_count = sum(1 for s in sentences if any(kw in s.lower() for kw in compound_keywords))
		compound_ratio = compound_count / total_sentences if total_sentences else 0.0
		features['复合句比例'] = compound_ratio

		# 衔接词密度：衔接词出现次数 / 总词数
		connectives = [
			# 中文
			'然而', '因此', '而且', '但是', '所以', '因为', '虽然', '并且', '如果', '不过', '即使', '然后', '于是',
			# 英文
			'however', 'therefore', 'moreover', 'but', 'so', 'because', 'although', 'and', 'if', 'though', 'even',
			'then', 'thus'
		]
		connective_count = sum(lower_content.count(kw.lower()) for kw in connectives)  # 转小写计数
		connective_density = connective_count / total_words if total_words else 0.0
		features['衔接词密度'] = connective_density

		return features

	# 这个函数是用来获取局部智能体的提示词的，输入是前一章的情节概要和当前章节的内容
	def __get_local_prompt(self, *, prev_plot, object_condition, next_content):
		return LOCAL_PROMPT_TEMPLATE.format(
			prev_plot = prev_plot,
			object_condition = object_condition,
			next_content = next_content
		)

	def __get_global_prompt(self, *, global_features):
		return GLOBAL_PROMPT_TEMPLATE.format(
			global_features = global_features
		)
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
			input_message = self.__get_local_prompt(prev_plot = self.__process_global_features(),
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
			# 以上的代码完成了对于每一章的局部评分和表面特征的提取，现在要进行全局评分的计算，现在我要提取每一章节的文字特征
			text_features = self.__get_text_features(chapter)
			print(f"第{len(self.global_features)}章的文字特征：", text_features)
			self.text_features.append(text_features) # 将每一章的文字特征存入成员变量中
		# 现在要计算出小说的平均文字特征得分，目前text_features存储了每一章的文字特征，接下来要计算平均值
		# 计算每一章的文字特征的平均值
		average_text_features = {}
		for feature in self.text_features :
			for key, value in feature.items() :
				if key not in average_text_features :
					average_text_features[key] = []
				average_text_features[key].append(value)
		# 计算平均值
		for key, values in average_text_features.items() :
			average_text_features[key] = sum(values) / len(values) if values else 0
		# 输出每一章的文字特征平均值
		print("每一章的文字特征平均值：", average_text_features)

		# 计算局部指标的平均值
		local_scores = {key: sum(values) / len(values) if values else 0 for key, values in self.local_scores.items()}
		print("所有章节的局部平均评分：", local_scores)
		# 现在需要计算全局评分
		global_plot = self.__process_global_features()
		response_global = await global_agent.run(
			task = self.__get_global_prompt(global_features = self.__get_global_prompt(global_features=global_plot))
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




