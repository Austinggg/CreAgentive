from autogen_agentchat.agents import AssistantAgent
from Resource.template.storygen_prompt.decision import decision_prompt_template
from Resource.tools.extract_last_content import extract_last_text_content
from Resource.tools.extract_llm_content import extract_llm_content
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock
from autogen_agentchat.messages import TextMessage
import json
import asyncio


async def score_plan(plan, model_client):
    """
    对单个plan进行评分

    该函数通过定义多个评估维度及其权重，利用评分Agent对方案进行分析，
    提取逻辑原子评分并计算加权综合得分。
    
    参数:
        plan (str): 待评分的计划内容
        model_client: 模型客户端对象，用于与评分Agent进行交互
        
    返回:
        float: 加权综合评分结果
    """

    # 定义每个评估维度的权重，TODO: 权重可以修改
    weights = {
        "p1": 0.1,  # 目标与角色动机背景一致性
        "p2": 0.15, # 目标对故事主线推动作用
        "p3": 0.1,  # 目标创新性
        "p4": 0.15, # 目标冲突引入效果
        "p5": 0.1,  # 目标情感共鸣效果
        "p6": 0.1,  # 计划可行性
        "p7": 0.1,  # 计划与角色匹配度
        "p8": 0.05, # 计划多角色互动
        "p9": 0.1,  # 计划风险悬念
        "p10": 0.05 # 计划连贯性吸引力
    }

    # 定义评分 Agent 用以对方案进行评分
    # TODO: 评分规则待完善
    scoreAgent = AssistantAgent(
        name="scoreAgent",
        description="根据评分模板对提取逻辑原子，对每个逻辑原子进行评分",
        model_client = model_client,
        system_message=decision_prompt_template
    )

    # Agent 分析得到的10个逻辑原子的值
    # prompt 要修改
    # 调通阶段，暂时不加  task，考虑使用 message 打包输入
    score_output = await scoreAgent.run(
        task=TextMessage(content=f"请按模板对下面方案评分：\n\n{plan}",source="user")
    )

    print("逻辑原子评分结果：")
    print(score_output)
    score_atoms_output = extract_llm_content(score_output) # 提取结果
    score_atoms_json = strip_markdown_codeblock(score_atoms_output) # 去除 json md 标记
    score_atoms = json.loads(score_atoms_json)  # 转成 dict
    print(f"score_atoms: {score_atoms}")

    # 加权综合评分算法
    weighted_score = 0 # 加权计算得分
    for key, value in score_atoms.items():
        if key in weights:
            weighted_score += value * weights[key]

    return weighted_score

    
async def evaluate_plan(plans,model_client):
    """
    对一组计划进行评分，并选出评分最高的计划。

    :param plans: 计划列表，每个计划是一个字典。
    :param model_client: 模型客户端实例，用于评分。
    :return: 最佳计划及其评分 (best_plan, best_score)。
    """

    plan_scores = []
    for plan in plans:
        # 计算每个故事方案的评分
        score = await score_plan(plan, model_client)
        
        # 将故事方案及其评分添加到列表中
        plan_scores.append((plan, score))

    # 选出评分最高的故事方案
    if plan_scores:
        best_plan, best_score = max(plan_scores, key=lambda x: x[1])
        
    else:
        best_plan, best_score = None, 0


    # 返回故事方案列表，最佳故事方案及评分
    return actual_best_plan, best_score
