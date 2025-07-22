from LLM_DNF_Novel.utils.prompt_templates import PROMPT_TEMPLATES
from llm import get_response_from_llm


class LLMExtractor:
    def extract_logic_atoms(self, text, task,background):
        """
        使用 LLM 提取逻辑原子
        :param text: 输入的文本
        :param task: 使用的任务模板（GoalEvaluation 或 PlanEvaluation）
        :return: 提取的逻辑原子字典
        """
        prompts = PROMPT_TEMPLATES.get(task, {})
        if not prompts:
            raise ValueError(f"Task '{task}' not found in PROMPT_TEMPLATES.")

        logic_atoms = {}
        for key, prompt in prompts.items():
            # 添加前缀到 full_prompt，并要求只返回 true 或 false
            full_prompt = f"You are a helpful assistant for evaluating text quality.\n{prompt}\nText: {text}\nbackground:{background}Please respond with only 'true' or 'false'."
            try:
                response = get_response_from_llm(full_prompt)
                logic_atoms[key] = response.strip()
            except Exception as e:
                print(f"Error during API call for {key}: {e}")
                logic_atoms[key] = "Error"
        print(f"Extracted logic atoms for task '{task}': {logic_atoms}")
        return logic_atoms
    
    
    
    
    
    
    
    
    
    
    

# if __name__ == "__main__":
#     llm_extractor = LLMExtractor()
#     decisions= [{'agent_name': '合并', 'goal': '确保团队安全并寻找可用物资，调查乘客失踪的传闻以应对潜在危机，同时评估环境威胁并制定初步生存计划，为邮轮事故和后续漂流求生做准备。', 'plan': '韩越将利用当前悠闲时间悄悄检查救生设备和物资储备点，并观察沈砚的动向以建立初步信任；江澈会整理乘客行为笔记并与友善乘客交谈，收集失踪传闻线索后与沈 砚分享；沈砚则以医生身份评估邮轮安全设施和逃生路线，并留意天气变化。若事故突发，韩越将引导乘客撤离并收集物资，同时与沈砚会合协作；沈砚会优先寻找韩越和江澈，利用 医疗技能稳定团队，并制定包含集合点、资源分配的生存计划；江澈持续记录线索，协助团队保持警惕。三人将共同承担探索、防御和决策职责，在漂流状态下确保团队生存。'}, 
#                 {'agent_name': '合并', 'goal': '韩越、江澈和沈砚三人协同行动，在邮轮上秘密检查救生设备和物资储备，收集失踪传闻线索，评估安全设施和逃生路线，同时留意天气变化和其他乘客的异常行为，为潜在的危机和邮轮事故做好全面准备。', 'plan': '韩越首先利用健身教练的身份作为掩护，假装进行常规的健身巡视，检查健身房附近的救生设备存放点，随后以 左脚扭伤需要休息为借口在甲板休息区停留，暗中观察救生艇的位置和状态，并留意沈砚是否出现在附近；同时，江澈整理乘客行为笔记，选择友善乘客交谈以收集失踪传闻线索，并 将整理好的信息与沈砚分享；沈砚则以例行检查的名义前往医疗室评估物资储备，观察沿途逃生路线和救生设备，与船员交谈了解天气预报和安全 protocols，并在甲板上留意气象变 化及韩越、江澈的动向；三人各自保持警觉，韩越用运动相机记录关键安全设备，沈砚准备简易急救包并制定集合点和逃生路线，最终三人汇合共享信息，为可能的事故制定协同应对 策略。'}, 
#                 {'agent_name': '合并', 'goal': '韩越、江澈和沈砚三人分工合作，韩越以左脚扭伤为借口在甲板休息区暗中观察救生艇的位置和状态，并留意沈砚是否出现，同时用运 动相机记录关键安全设备；江澈在甲板上与友善乘客交谈，收集关于失踪传闻的线索，并留意救生设备的位置和状态；沈砚在医疗室评估物资储备的同时，留意船员对安全 protocols 的解释漏洞，并暗中记录关键医疗物资和逃生路线，三人共同为潜在的邮轮危机做准备。', 'plan': '韩越首先假装因左脚扭伤在甲板休息区休息，选择一个视野开阔的位置，利用运 动相机拍摄周围的“风景”，实则重点记录救生艇的位置、状态以及附近的逃生路线，同时留意是否有沈砚的身影；如果发现沈砚，韩越会尝试用眼神或轻微的手势引起他的注意，但避 免明显的接触。与此同时，江澈整理近几日记录的乘客行为笔记，选择几位友善且可能知情的乘客，以分享照片为由自然地接近他们，从闲聊开始逐步引导话题到失踪传闻，观察对方 反应并收集信息，同时留意救生设备的位置和状态。沈砚则前往医疗室，以例行检查名义清点急救药品和手术器械，故意询问船员关于急救演练的情况以观察其反应，并在无人时绘制 逃生路线图；之后，沈砚以检查防晒伤药品储备为由接触甲板船员，实际观察救生艇释放机制和海平面情况，并偷偷将关键医疗物资装入随身急救包。三人各自完成任务后，寻找机会 汇合并共享信息，为后续可能的危机做好准备。'}, 
#                 {'agent_name': '合并', 'goal': '韩越、江澈和沈砚三人分工合作，暗中记录救生艇位置和逃生路线、收集关于失踪传闻的线索 、观察船员的安全操作流程，并为潜在的邮轮危机做好准备。', 'plan': '韩越首先在甲板休息区选择一个视野开阔的位置，假装因左脚扭伤休息，将运动相机固定在显眼但不易被怀 疑的位置，调整角度以覆盖救生艇和逃生路线，并开启录像功能，同时用余光留意沈砚是否出现；江澈则整理乘客行为笔记，筛选出友善且可能知情的乘客，以分享照片为由接近他们 ，引导话题到失踪传闻，并在交谈过程中留意救生设备的位置和状态；沈砚前往医疗室，假装阅读医学杂志，暗中观察医疗室的物资储备情况，与船员闲聊并询问急救演练流程，同时 绘制从医疗室到最近救生艇的路线图，并悄悄将关键医疗物资装入随身急救包；三人在各自任务完成后寻找机会汇合，共享收集到的信息，为后续可能的危机做好准备。'}
#                 ]
#     # 提取逻辑原子  
#     for decision in decisions:
#         goal = decision["goal"]
#         plan = decision["plan"]
#         logic_atoms_goal = llm_extractor.extract_logic_atoms(goal, task="GoalEvaluation")
#         print(logic_atoms_goal)
#         logic_atoms_plan = llm_extractor.extract_logic_atoms(plan, task="PlanEvaluation")
#         print(logic_atoms_plan)