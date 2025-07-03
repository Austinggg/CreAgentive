# CreAgentive

CreAgentic 是一个基于 Autogen 框架实现的基于多智能体的创意文本生成工作流。

## 创建环境

```cmd
conda create -n creagentic python=3.10
conda activate creagentic
pip install -r requirement.txt
```

自行配置 `.env` 文件存储 API Key

## 项目说明

项目结构按照 HAWK 的层次架构进行分布。

```raw
CreAgentic
├── .env                  # LLM API Key 和相关环境配置
├── workflow              # 定义项目的各种 Agent 工作流，包括总的工作流和各个小模块内部的工作流
│   └── main_wk.py        # 主工作流
├── operator              # 暂时对应到 Autogen 中的 创建实现各种功能的 Team
│   ├── memory.py         # 关于 memory 的相关操作
│   ├── environment.py    # 关于文本交互环境的相关操作
│   └── management.py     # 关于 Agent 的各项操作
├── agent                 # 定义会用到的各种 Agent 的类
│   ├── MemoryAgent.py        # 定义记忆 Agent 的类
│   ├── WriterAgent.py        # 定义写作 Agent 的类
│   ├── CharacterAgent.py     # 定义角色 Agent 的类
│   └── DecisionAgent.py      # 定义决策 Agent 的类
└── resources
    ├── memory               # 存放项目中的各种数据，包括 agent state、kg、角色定义等
    │   ├── AgentState       # 以 json 格式存放
    │   └── character        # 角色的基本信息，json格式存放
    ├── tools                # 存放各种 Agent 会用到的 Function 和 Tool
    └── llmclient.py         # 配置 llm client
```
