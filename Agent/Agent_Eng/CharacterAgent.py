from typing import AsyncGenerator, Sequence
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_core import CancellationToken
from Agent.Agent_Eng.MemoryAgent import MemoryAgent
import uuid


class CharacterAgent(BaseChatAgent):
	"""
	CharacterAgent is defined based on the Autogen framework and is used to simulate
	agents with specific role settings. Supports custom role information and specifying
	a client for text generation.
	"""

	def __init__(self, name: str, personality: str, gender: str, role: str,
	             memory: str, relationships: str, client):
		"""
		Initialize a CharacterAgent instance.

		:param name: The name of the agent
		:param personality: The personality description of the agent
		:param client: The client instance used for text generation
		"""
		super().__init__(name = name, client = client)
		self.id = str(uuid.uuid4())
		self.personality = personality
		self.gender = gender
		self.tmp_memory = []
		self.state = {
			"role": role,
			"memory": memory,
			"relationships": relationships
		}

	@property
	def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
		return (TextMessage,)

	async def on_messages(self, messages: Sequence[BaseChatMessage],
	                      cancellation_token: CancellationToken, chapter: int) -> Response:
		"""
		Extract valid content from received messages, populate relevant role information,
		and generate a reply message.

		:param messages: List of received messages
		:param cancellation_token: Cancellation token for aborting operations
		:return: Generated reply message
		"""
		name = self.name
		# Temporary memory, events generated before decision-making, do not update
		# the knowledge graph but need to be used in this round of interaction
		# to show plot changes
		# Read character state (read knowledge graph, obtain relevant information)
		memory = MemoryAgent()
		character_memory = memory.get_character_memory(name, chapter)  # Assuming chapter
		# Generate reply content
		prompt = messages[-1].content if messages else ""
		full_prompt = (f"You are now {self.name}, please reply as this character: {prompt}, "
		               f"the information you know is: {character_memory}. What just happened: {self.tmp_memory}")
		result = self.client.chat.completions.create(
			messages = [{"role": "user", "content": full_prompt}],
			max_tokens = 4096
		)
		content = (result.choices[0].message.content.strip()
		           if result.choices else "Generation failed")
		msg = TextMessage(content = content, source = name)
		# Generate response
		response = Response(chat_message = msg, inner_messages = [msg])
		# Update temporary memory
		self.tmp_memory.append(msg)
		return response

	async def on_messages_stream(
			self, messages: Sequence[BaseChatMessage],
			cancellation_token: CancellationToken
	) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
		prompt = messages[-1].content if messages else ""
		full_prompt = f"You are now {self.description}, please reply as this character: {prompt}"
		result = self.client.chat.completions.create(
			messages = [{"role": "user", "content": full_prompt}],
			max_tokens = 4096
		)
		content = (result.choices[0].message.content.strip()
		           if result.choices else "Generation failed")
		msg = TextMessage(content = content, source = self.name)
		yield msg
		yield Response(chat_message = msg, inner_messages = [msg])

	async def on_reset(self, cancellation_token: CancellationToken) -> None:
		# Optional: Reset Agent state
		pass

	async def on_update(self, cancellation_token: CancellationToken) -> dict:
		# Update knowledge graph, add new characters or character information changes
		character = {
			"id": self.id,
			"name": self.name,
			"personality": self.personality,
			"gender": self.gender,
			"state": self.state
		}
		return character
