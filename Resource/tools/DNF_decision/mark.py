from LLM_DNF_Novel.models.RuleBasedDNF import RuleBasedDNF
from LLM_DNF_Novel.models.dnf_model import DNFModel
import torch
from LLM_DNF_Novel.utils.evaluation import evaluate
from LLM_DNF_Novel.utils.logic_transform import transform_logic_atoms_to_features

def load_trained_model(model_path, num_features, num_conjuncts, num_classes, device):
    """
    加载训练过的模型。
    :param model_path: 模型文件路径。
    :param num_features: 特征数量。
    :param num_conjuncts: 合取项数量。
    :param num_classes: 类别数量。
    :param device: 设备（CPU 或 GPU）。
    :return: 加载的模型。
    """
    # 初始化模型
    model = DNFModel(num_features=num_features, num_conjuncts=num_conjuncts, num_classes=num_classes)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()  # 设置为评估模式
    print(f"Model loaded from {model_path}")
    return model

def score_goal_and_plan(goal, plan, llm_extractor, goal_predicate_set, plan_predicate_set, device, background):
    """
    使用训练过的模型对 goal 和 plan 进行评分，并返回总分。
    :param goal: 决策中的目标。
    :param plan: 决策中的计划。
    :param llm_extractor: LLM 提取器实例。
    :param goal_predicate_set: goal 的谓词集合。
    :param plan_predicate_set: plan 的谓词集合。
    :param model: 训练过的 DNF 模型。
    :param device: 设备（CPU 或 GPU）。
    :return: goal 和 plan 的总评分。
    """
    # 使用 GoalEvaluation 模板对 goal 进行评分
    logic_atoms_goal = llm_extractor.extract_logic_atoms(goal, task="GoalEvaluation",background=background)
    features_goal = transform_logic_atoms_to_features(logic_atoms_goal, goal_predicate_set)
    print(f"features_goal: {features_goal}")
    # 使用 PlanEvaluation 模板对 plan 进行评分
    logic_atoms_plan = llm_extractor.extract_logic_atoms(plan, task="PlanEvaluation",background=background)
    features_plan = transform_logic_atoms_to_features(logic_atoms_plan, plan_predicate_set)
    print(f"features_plan: {features_plan}")
    # 将 goal 和 plan 的特征拼接为模型输入
    features = torch.cat([features_goal, features_plan]).unsqueeze(0).to(device)
    model = RuleBasedDNF(num_features=features.size(1), num_conjuncts=4, num_classes=2)
    
    model.set_conjunctions([
        {0: 6, 4: -6},          # conj0 = P1 ∧ ¬P5
        {2: 6, 6: 6, 9: -6},    # conj1 = P3 ∧ P7 ∧ ¬P10
        {1: 6, 3: 6},           # conj2 = P2 ∧ P4
        {5: -6, 7: 6}           # conj3 = ¬P6 ∧ P8
    ])
    model.set_disjunctions({
        0: {0: 6, 1: 6},        # 类别0 = conj0 ∨ conj1
        1: {2: 6, 3: 6}         # 类别1 = conj2 ∨ conj3
    })
    model.to(device)
    with torch.no_grad():
        output = model(features)  # 模型输出
        score = output[0, 1].item()  # 提取第 1 类的概率（假设第 1 类为高质量决策）
    return score    
