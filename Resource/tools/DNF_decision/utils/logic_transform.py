import torch

def transform_logic_atoms_to_features(logic_atoms, predicate_set):
    """
    将逻辑原子转换为 DNF 模型的输入特征。
    :param logic_atoms: 逻辑原子字典
    :param predicate_set: 逻辑谓词集合
    :return: 特征向量
    """
    features = []
    for predicate in predicate_set:
        features.append(1 if logic_atoms.get(predicate, "false") == "true" else 0)
    return torch.tensor(features, dtype=torch.float32)

