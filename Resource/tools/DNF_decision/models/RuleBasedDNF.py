import torch
import torch.nn as nn

class RuleBasedDNF(nn.Module):
    """
    基于规则的 DNF 模型（无需训练，直接使用手动定义的逻辑规则进行分类）。

    逻辑结构：
      - 合取层（Conjunctions）: 多个 AND 规则。
      - 析取层（Disjunctions）: 每个类别通过 OR 将若干合取规则连接。

    特点：
      1. 支持手动设置合取规则和析取规则。
      2. 直接以布尔或 [0,1] 连续值为输入，输出各类别的激活值。
      3. 提供可读规则展示功能。
    """
    def __init__(self, num_features: int, num_conjuncts: int, num_classes: int):
        """
        初始化模型结构。

        Args:
            num_features    (int): 输入特征维度。
            num_conjuncts   (int): 合取规则（AND 子句）的数量。
            num_classes     (int): 输出类别数量。
        """
        super().__init__()
        self.num_features = num_features
        self.num_conjuncts = num_conjuncts
        self.num_classes = num_classes
        # 存储合取规则的列表，每条规则为字典 {feature_index: sign}
        self.conj_rules: list[dict[int, int]] = []
        # 存储析取规则的字典 {class_index: [conj_rule_indices]}
        self.disj_rules: dict[int, list[int]] = {}

    def set_conjunctions(self, rules: list[dict[int, int]]):
        """
        设置合取规则（AND 子句）。

        每条规则规则格式为 {feat_idx: sign}：
          sign = +1 表示 P_feat_idx 为真（值趋于 1）
          sign = -1 表示 ¬P_feat_idx（取反后趋于 1）

        Args:
            rules (list[dict]): 合取规则列表。
        """
        # 直接替换规则列表，无需梯度。
        self.conj_rules = rules

    def set_disjunctions(self, rules: dict[int, dict[int, int]]):
        """
        设置析取规则（OR 子句）。

        格式为 {class_idx: {conj_rule_idx: 任意值}}，
        这里只关心 conj_rule_idx 列表，用于 OR 连接。

        Args:
            rules (dict): 析取规则字典。
        """
        # 提取各类别对应的合取规则索引列表
        self.disj_rules = {c: list(conjs.keys()) for c, conjs in rules.items()}

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向计算：
          1. 计算每条合取规则的激活值（AND 运算）。
          2. 对每个类别，将其对应合取规则取最大值（OR 运算）。

        Args:
            x (torch.Tensor): 输入张量，形状 [B, num_features]。
                               值可为 0/1 布尔，也可在 [0,1] 范围内表示强度。

        Returns:
            torch.Tensor: 输出张量，形状 [B, num_classes]。
                          每个元素为该类别下 OR 后的最大激活值。
        """
        B = x.size(0)
        device = x.device

        # ----- 1. 合取层（AND）计算 -----
        # 初始化合取层输出，shape = [B, num_conjuncts]
        conj_vals = torch.zeros(B, self.num_conjuncts, device=device)
        # 对每条合取规则进行逐特征累乘
        for i, rule in enumerate(self.conj_rules):
            # v 初始化为全 1，表示空 AND 子句的中性元素
            v = torch.ones(B, device=device)
            for feat_idx, sign in rule.items():
                if sign > 0:
                    # P_feat_idx：直接用 x[:, feat_idx]
                    v = v * x[:, feat_idx]
                else:
                    # ¬P_feat_idx：用 (1 - x[:, feat_idx])
                    v = v * (1.0 - x[:, feat_idx])
            conj_vals[:, i] = v

        # ----- 2. 析取层（OR）计算 -----
        # 初始化析取层输出，shape = [B, num_classes]
        disj_vals = torch.zeros(B, self.num_classes, device=device)
        # 对每个类别，取其所有合取规则输出的最大值
        for class_idx, conj_idxs in self.disj_rules.items():
            if len(conj_idxs) > 0:
                # torch.max 返回 (values, indices)，这里只需 values
                disj_vals[:, class_idx] = torch.max(conj_vals[:, conj_idxs], dim=1)[0]
            # 若 conj_idxs 为空，则保持为 0（永不激活）

        return disj_vals

    def get_rules(self) -> dict[str, list[str] | dict[int, str]]:
        """
        生成并返回可读的规则文本。

        Returns:
            dict: 包含 'conjunctions' 和 'disjunctions' 两部分，
                  分别为合取和析取的可读字符串列表或字典。
        """
        # 可读合取规则
        conj_readable: list[str] = []
        for i, rule in enumerate(self.conj_rules):
            terms = []
            for feat_idx, sign in rule.items():
                # Pj 或 ¬Pj
                term = f"P{feat_idx+1}" if sign > 0 else f"¬P{feat_idx+1}"
                terms.append(term)
            # 若无任何条件，则表示空子句
            clause = " ∧ ".join(terms) if terms else "∅"
            conj_readable.append(f"conj{i} = {clause}")

        # 可读析取规则
        disj_readable: dict[int, str] = {}
        for class_idx, conj_idxs in self.disj_rules.items():
            if conj_idxs:
                clause = " ∨ ".join(f"conj{j}" for j in conj_idxs)
            else:
                clause = "∅"
            disj_readable[class_idx] = clause

        return {
            "conjunctions": conj_readable,
            "disjunctions": disj_readable
        }


