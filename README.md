# CreAgentive

CreAgentive is An Agent Workflow Driven Multi-Category Creative Generation Engine

## 🛠️ Environment Setup

1. Neo4j Graph Database Configuration.
   - Install Neo4j (Community Edition or Neo4j Desktop recommended).
   - Enable the APOC plugin.

2. Python Environment & Dependencies

```cmd
# Create a Conda environment with Python 3.10
conda create -n creagentive python=3.10

# Activate the environment
conda activate creagentive

# Install required packages
pip install -r requirements.txt
```

3. Environment Variables
Create a .env file in the project root and fill in your credentials:

```raw
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Neo4j Connection Settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

## ▶️ Running the Project

1. Start Neo4j

```cmd
neo4j console
```

2. Test Neo4j Connection

```cmd
python ./resource/ds_neo4j_client.py
```

A successful run (no errors) confirms connectivity.


3. Generate Stories

```cmd
python main_Eng.py # Generate English story
python main.py # Generate Chinese story
```


