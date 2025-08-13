from Workflow.Accessmen_wk_in_Eng import AccessmentWorkflow
from Resource.llmclient import LLMClientManager
import asyncio
async def main():
	model_client = LLMClientManager().get_client("deepseek-v3")
	accessmentworkflow = AccessmentWorkflow(model_client)
	# accessmentworkflow.initialize_chapters(r"C:\Users\pcw\Desktop\Recent_files\Agentnovel\access_novel\Cre")
	result = await accessmentworkflow.run(chapters = r"C:\Users\pcw\Desktop\Recent_files\Agentnovel\access_novel\Cre") # 运行评价工作流/
	print(result)

if __name__ == "__main__":
	asyncio.run(main())