from models.dnf_model import DNFModel
import torch

def save_predefined_model():
    """
    使用预设参数初始化模型并保存。
    """
    # 配置参数
    num_features = 10  # 特征数量
    num_conjuncts = 20  # 合取项数量
    num_classes = 2  # 类别数量
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 初始化模型
    model = DNFModel(num_features=num_features, num_conjuncts=num_conjuncts, num_classes=num_classes)
    model.to(device)

    # 设置预设参数（示例：将所有权重初始化为固定值）
    with torch.no_grad():
        for param in model.parameters():
            param.fill_(0.5)  # 将所有参数设置为 0.5（根据需要调整）

    # 保存模型
    torch.save(model.state_dict(), "dnf_model_predefined.pt")
    print("Predefined model saved to dnf_model_predefined.pt")
    
    
if __name__ == "__main__":
    save_predefined_model()