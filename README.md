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
├── workflow
├── operator
│   └── memory.py
├── agent
│   ├── MemoryAgent.py
│   └── WriterAgent.py
└── resources
    ├── memory
    ├── tools
    └── llmclient.py
```