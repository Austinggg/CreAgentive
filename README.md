# CreAgentive

CreAgentive 是一个基于 Autogen 框架实现的基于多智能体的创意文本生成工作流。

## 创建环境

### 

本地需要安装 neo4j 图数据库，参考博客：https://blog.csdn.net/AustinCyy/article/details/149020499
安装完 Neo4j 后需要安装 apoc 插件，参考博客：https://blog.csdn.net/shdabai/article/details/132880323

### conda 创建环境并安装依赖包

```cmd
conda create -n creagentive python=3.10
conda activate creagentive
pip install -r requirement.txt
```

在项目根目录中创建一个文件并添加您的 OpenAI API 密钥 和 Neo4j 的账密和端口： `.env`

```raw
OPENAI_API_KEY=<your_openai_api_key>

# Neo4j 配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=******
```


## 运行项目

启动 ne04j 图数据库

```cmd
# 启动 neo4j 图数据库
neo4j console
# 测试能否成功连接图数据库
python .\resource\ds_neo4j_client.py 
```

## 项目说明

项目结构按照 HAWK 的层次架构进行分布。

```raw
CreAgentive
├── .env                  # LLM API Key 和相关环境配置
├── Workflow/                        # 工作流模块，包含各类流程定义
│   ├── Init_wk.py                   # 初始化工作流，用于创建智能体和构建初始化流程
│   ├── StoryGen_wk.py               # 故事生成工作流，用于生成故事内容
│   └── Write_wk.py                  # 写作工作流，用于内容创作
│
├── Operator/                        # 运营模块，包含环境和管理类
│   ├── environment.py               # 环境配置，包含 Neo4j 和 LLM 客户端初始化
│   ├── manage.py                    # 管理类，用于统一管理和调度各类 Agent
│   └── memory.py                    # 记忆管理模块，用于处理角色记忆和知识图谱
│
├── Agent/                           # 智能体模块，包含各类 Agent 的实现
│   ├── CharacterAgent.py            # 角色智能体，模拟特定角色行为
│   ├── DecicionAgent.py             # 决策智能体，用于生成决策建议
│   ├── InitializeAgent.py           # 初始化智能体，用于系统初始化配置
│   ├── MemoryAgent.py               # 记忆智能体，用于记忆存储和检索
│   └── WriteAgent.py                # 写作智能体，用于内容生成
│
├── Resource/                        # 资源模块，包含模板、工具、配置和数据
│   ├── story/                       # 工作流运行生成的完整故事                 
│   │
│   ├── memory/                      # 存储各类记忆数据
│   │   ├── character/               # 按章节划分的角色记忆
│   │   │   ├── chapter_1_memories/  # 第一章的记忆数据
│   │   │   ├── chapter_2_memories/  # 第二章的记忆数据
│   │   │   └── chapter_3_memories/  # 第三章的记忆数据
│   │   │
│   │   ├── init/                    # 初始化相关数据 （初始化结果将作为 chapter0 的记忆数据）
│   │   │   ├── chapter_data.json    # 章节数据
│   │   │   ├── full_result.json     # 初始化流程的完整执行结果
│   │   │   ├── init_config.json     # 初始化配置文件
│   │   │   └── initial_data.json    # 初始数据模板
│   │   │
│   │   └── story_plan/              # 故事方案数据
│   │       ├── chapter1.json        # 第一章故事规划
│   │       ├── chapter2.json        # 第二章故事规划
│   │       ├── chapter3.json        # 第三章故事规划
│   │       └── initial_data.json    # 故事初始数据模板 （将改名成 chapter0.json）
│   │
│   ├── template/                    # 提示词模板资源
│   │   ├── init_prompt/             # 初始化工作流提示词模板
│   │   │   ├── extractor.py         # 提取器模板
│   │   │   ├── initializer.py       # 初始化器模板
│   │   │   ├── structurer.py        # 结构化模板
│   │   │   └── validator.py         # 验证器模板
│   │   │ 
│   │   ├── write_prompt/            # 写作工作流提示词模板 
│   │   │
│   │   ├── storygen_prompt/         # 故事生成工作流提示词模板
│   │   │
│   │   └── struct_init.py           # 结构初始化模板
│   │
│   ├── tools/                       # 工具库
│   │   ├── CustomJSONEncoder.py     # 自定义 JSON 编码器
│   │   ├── kg_builder.py            # 知识图谱构建工具
│   │   └── strip_markdown_codeblock.py # 去除 Markdown 代码块标记
│   │
│   ├── ds_neo4j_client.py           # Neo4j 客户端配置
│   └── llmclient.py                 # LLM 客户端管理
```

故事生成工作流 生成的每一章方案 存放在 resource/memory/story_plan
生成的


## Todo

1. MemoryAgent 的文件路径设置修改
2. kg_builder.py 中需要修改 单向关系 为双向关系
3. 故事生成工作流的实现
4. 写作工作流的实现
5. 测试文件的外部实现
6. 各项文件保存路径的修改
7. 各项中间提示词的格式校对


