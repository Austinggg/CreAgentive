import torch
import torch.nn as nn

class DNFModel(nn.Module):
    def __init__(self, num_features, num_conjuncts, num_classes):
        super(DNFModel, self).__init__()
        self.num_features = num_features
        self.num_conjuncts = num_conjuncts
        self.num_classes = num_classes

        # 定义合取项（Conjunctions）和析取项（Disjunctions）的权重
        self.conjunctions = nn.Linear(num_features, num_conjuncts, bias=False)
        self.disjunctions = nn.Linear(num_conjuncts, num_classes, bias=False)

    def forward(self, x):
        # 计算合取项
        conjuncts = torch.sigmoid(self.conjunctions(x))
        # 计算析取项
        disjuncts = torch.sigmoid(self.disjunctions(conjuncts))
        print(f"conjuncts: {conjuncts}")
        print(f"disjuncts: {disjuncts}")
        # 返回每个类的概率 
         
        return disjuncts