# CreAgentive

CreAgentive 是一个基于 Autogen 框架实现的基于多智能体的创意文本生成工作流。

## 创建环境

### Neo4j 图数据库配置

本地需要安装 neo4j 图数据库，参考博客：`https://blog.csdn.net/AustinCyy/article/details/149020499`
安装完 Neo4j 后需要安装 apoc 插件，参考博客：`https://blog.csdn.net/shdabai/article/details/132880323`

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


故事生成工作流 生成的每一章方案 存放在 [Resource/memory/story_plan](Resource/memory/story_plan)
生成的故事存储在 [Resource/memory/story](Resource/memory/story)

## Todo

- storygen_wk 的修改完善，消除 KG 检索的 bug
- init_wk 的修改完善，需与 storygen_wk 配合
- writing_wk 的修改完善
- 修改三个工作流，使其能够流畅运行
- 修改 storygen_wk 的提示词，让其生成过程加上 章节限制
- 修改提示词为中英两版
- 对项目代码进行修缮，确保异步函数等的精确实现，去掉多余的代码和注释。
- 产出中英文小说。
