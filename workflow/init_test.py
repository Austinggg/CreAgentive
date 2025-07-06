from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.agents import UserProxyAgent, AssistantAgent
from autogen_core.memory import ListMemory, MemoryContent
from resource.llmclient import LLMClientManager
from resource.template.init import demand_template, init_info_template
from datetime import datetime
import json
import asyncio
import collections # 导入 collections 模块用于 deque
import os
import yaml

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()  # 将 datetime 转换为 ISO 格式的字符串
        if isinstance(o, set):
            return list(o)  # 将 set 转换为 list
        return super().default(o)


# 1. 初始化模型客户端和测试输入
# 初始化大型语言模型 (LLM) 客户端，指定使用 "deepseek-v3" 模型。
model_client = LLMClientManager().get_client("deepseek-v3")

# 定义一个双端队列 (deque) 来存储自动化测试的模拟用户输入。
# 队列中包含一个预设的、详细的故事需求描述，用于测试代理的工作流程。
test_inputs = collections.deque([
    "我想要一个悬疑的故事，里面要3个主人公，荒岛求生的类型" +
    "故事的背景设定在一个神秘的荒岛上，主人公们需要面对未知的挑战和危险。" +
    "希望故事风格轻松幽默，语言风格简洁明了。"
])

def automated_input_func(prompt):
    """
    自定义输入函数，用于自动化测试场景。
    当系统需要用户输入时，此函数会从 `test_inputs` 队列中按序取出预设的输入字符串。
    如果队列为空，表示所有预设输入已用尽，函数将返回一个空字符串。
    """
    if not test_inputs:
        print("\n[自动化测试]: 没有更多预设输入。退出或提供空字符串。")
        return "" # 如果没有更多输入，返回空字符串或引发错误
    next_input = test_inputs.popleft() # 从队列的左侧（前端）移除并返回一个元素
    print(f"\n[自动化测试]: 模拟用户输入: {next_input}")
    return next_input

# 2. 实例化代理
# 实例化用户代理 (`UserProxyAgent`)。
# 此代理模拟用户与系统的交互，其输入来源通过 `input_func` 参数设置为自动化测试函数。
user_proxy = UserProxyAgent(name="user_input", input_func=automated_input_func)

# 实例化提取器代理 (`AssistantAgent`)。
# 职责：从用户的自然语言描述中识别并提取关键信息，然后将其结构化填充到预定义的需求模板中。
extractor = AssistantAgent(
    name="extractor",
    model_client=model_client,
    system_message=(
        "你是一个结构化字段提取助手，从用户自然语言中提取并补充到下面的需求模板中。\n" +
        f"{demand_template} 这是当前需求模板的结构。\n" +
        "将这些字段存入模板中。未提到的不修改。"
    )
)

# 打印提取器代理的系统消息，以便验证其配置和理解的需求模板结构。
print("当前需求模板结构:")
print(extractor._system_messages)

# 实例化验证器代理 (`AssistantAgent`)。
# 职责：检查当前需求模板中的所有字段是否都已完整填充（即没有 None 值）。
# 如果不完整，它会明确地向用户代理追问缺失的信息；如果完整，则回复“完整”。
validator = AssistantAgent(
    name="validator",
    model_client=model_client,
    system_message=(
        "你是一个需求验证助手，负责检查当前模板是否完整（所有字段非 None）。\n" +
        "如果模板不完整，请针对缺失字段向用户提出明确的追问。例如：‘请补充[缺失字段名]’。\n" +
        "如果模板已完整，请只回复一个词：‘完整’。不要添加任何其他文字或标点符号。"
    )
)

# 实例化结构化器代理 (`AssistantAgent`)。
# 职责：在需求模板被验证为完整后，以预定义的结构化 JSON 格式输出最终的需求模板内容。
structurer = AssistantAgent(
    name="structurer",
    model_client=model_client,
    system_message=(
        "你负责输出最终完整的需求模板，以需求模板的结构返回。下面是模板结构:\n" +
        f"{demand_template}"
    )
)

# 打印结构化器代理的系统消息，确认其输出格式要求。
print("当前结构化模板代理的系统消息:")
print(structurer._system_messages)

# 将初始化信息模板（一个Python字典）转换为格式化的 JSON 字符串。
# `ensure_ascii=False` 确保中文字符在 JSON 输出中正确显示，而不是被转义。
init_info_template_str = json.dumps(init_info_template, indent=2, ensure_ascii=False)

# 实例化初始化器代理 (`AssistantAgent`)。
# 职责：根据已完成并验证的用户需求模板，生成相应的系统初始化配置。
# 此过程是内部的，不涉及与用户的额外交互。
initializer = AssistantAgent(
    name="initializer",
    model_client=model_client,
    system_message=(
        "你是系统初始化助手，根据已完成的用户需求模板生成初始化配置。\n\n" +
        "请按照下面的初始始化信息模板（无需和用户交互）进行初始化：\n\n" +
        f"{init_info_template_str} \n\n" +
        "请确保生成的配置项符合需求模板的结构和内容要求。\n" +
        "注意生成的内容不要带有 markdown 格式或其他格式化标记，"
    )
)

# 打印初始化器代理的系统消息，显示其参考的初始化模板。
print(initializer._system_messages)

print("智能体创建完成") # 确认所有智能体（代理）已成功初始化。

# 3. 构建流程图
# 创建 `DiGraphBuilder` 实例，用于可视化和管理代理之间的有向图工作流。
builder = DiGraphBuilder()

# 将所有已实例化的代理添加为工作流图中的节点。
builder.add_node(user_proxy)
builder.add_node(extractor)
builder.add_node(validator)
builder.add_node(structurer)
builder.add_node(initializer)

# 定义代理之间的消息传递路径（边）及其触发条件。
builder.add_edge(user_proxy, extractor)
builder.add_edge(extractor, validator)
builder.add_edge(validator, user_proxy, condition=lambda msg: "完整" not in msg.content)
builder.add_edge(validator, structurer, condition=lambda msg: msg.content.strip() == "完整")
builder.add_edge(structurer, initializer)

# 设置工作流的起始点为用户代理 (`user_proxy`)，表示流程从用户输入开始。
builder.set_entry_point(user_proxy)

# 构建最终的工作流有向图。
graph = builder.build()

# 确认图结构已正确构建，所有节点和边均已按预期添加。
# print("图结构校验通过，节点和边已正确添加。")

# 4. 创建 GraphFlow
# 创建 `GraphFlow` 实例，这是整个多智能体工作流的执行引擎。
# 它将协调 `participants` 列表中所有代理之间的消息传递，并按照 `graph` 定义的流程执行。
flow = GraphFlow(
    participants=[user_proxy, extractor, validator, structurer, initializer],
    graph=graph
)

# print("GraphFlow 创建完成。") # 确认 `GraphFlow` 实例已成功创建。

# 5. 运行流程
# 定义 `run` 函数，用于启动并执行整个多智能体工作流。
def run():
    result = asyncio.run(flow.run())

    save_dir = "./resource/init"
    os.makedirs(save_dir, exist_ok=True)

    # 1. 保存 initializer 输出
    for msg in result.messages:
        if msg.source == "initializer":
            content = msg.content
            save_path = os.path.join(save_dir, "output_init_config.json")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"\n✅ 初始化配置已保存至 {save_path}")

    # 2. 保存完整 result（JSON + 自定义编码器）
    full_result_path = os.path.join(save_dir, "full_result.json")
    output_data = {
        "__metadata__": {
            "description": "完整多智能体执行结果",
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0"
        },
        "data": result.model_dump()
    }
    with open(full_result_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
    print(f"\n✅ 完整执行结果已保存至 {full_result_path}")

    # 3. （可选）保存为 YAML 格式（更适合人工查看）
    yaml_path = os.path.join(save_dir, "full_result.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(output_data, f, allow_unicode=True, sort_keys=False)
    print(f"✅ 完整执行结果（YAML）已保存至 {yaml_path}")

    return result

# 当此 Python 脚本作为主程序直接运行时，调用 `run()` 函数以启动工作流。
if __name__ == "__main__":
    run()
