import torch
from Resource.tools.DNF_decision.mark import score_goal_and_plan, load_trained_model
from Resource.tools.DNF_decision.models.llm_extractor import LLMExtractor
def evaluate_decisions(decisions, llm_extractor,background):
    """
    对一组决策进行评分，并选出评分最高的决策。
    
    :param decisions: 决策列表，每个决策包含 "goal" 和 "plan"。
    :param llm_extractor: LLM 提取器实例。
    :param predicate_set: 谓词集合，用于特征转换。
    :param model: 训练过的 DNF 模型。
    :param device: 设备（CPU 或 GPU）。
    :return: 包含每条决策评分的列表，以及评分最高的决策和分数。
    """
    decision_scores = []
    for decision in decisions:
        goal = decision["goal"]
        plan = decision["plan"]
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        goal_predicate_set = ["p1","p2","p3","p4","p5"]  
        plan_predicate_set = ["p6","p7","p8","p9","p10"]
        score = score_goal_and_plan(goal, plan, llm_extractor, goal_predicate_set, plan_predicate_set, device,background)
        decision_scores.append((decision, score))

    # 输出每条决策的评分
    for i, (decision, score) in enumerate(decision_scores):
        print(f"Decision {i + 1}: {decision}, Score: {score}")

    # 选出评分最高的决策
    best_decision, best_score = max(decision_scores, key=lambda x: x[1])
    print(f"\nBest Decision: {best_decision}, Score: {best_score}")

    return decision_scores, best_decision, best_score