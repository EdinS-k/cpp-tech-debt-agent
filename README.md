# 技术债务多 Agent 分析系统

基于 LangGraph 多 Agent 协作 + 混合检索 RAG 的 C++ 代码技术债务分析工具。

用户在网页上提问或上传代码，系统依次完成「代码解析 → 风险评估 → 总结报告」，
并把分析结果沉淀为可检索的长期记忆。

---

## 功能

- **多 Agent 协作**：LangGraph 状态图编排三个专职 Agent，含预检短路与条件分支
- **混合检索 RAG**：向量语义检索 + BM25 关键词检索，RRF 融合
- **双层记忆**：短期（多轮对话）+ 长期（结构化债务记录）
- **Function Calling**：风险评估 Agent 自主选择检索策略
- **聊天式交互**：SSE 流式输出，打字机效果 + Markdown 渲染
- **代码上传**：支持上传 C/C++ 文件，或使用内置示例

---

## 架构

```
浏览器  static/index.html
   │  POST /upload   上传代码
   │  GET  /analyze  SSE 流式
   ▼
main.py  FastAPI + sse-starlette
   │  graph.stream(state, thread_id)
   ▼
agent/   ⓪预检 ──[非代码]────────────────────────────────────────► END
           └─[是代码]─► ①代码解析 ─► ②风险评估 ─┬─[有高风险]─► ③详细总结 ─┐
                                               └─[无高风险]─► 简短总结 ─┴─► END
   │
   ▼
tools/   code_tools · memory_tools · retrieval_tools
   │
   ▼
resources/  llm · embedding · sqlserver_store · rag_pipeline
```

依赖方向严格单向：`resources ← tools ← agent ← main`

---

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | 原生 HTML / CSS / JS、SSE (EventSource)、FileReader、localStorage |
| Web | FastAPI · Uvicorn · sse-starlette · Pydantic |
| Agent | LangGraph · LangChain · langchain-openai |
| LLM | DeepSeek `deepseek-flash`（OpenAI 兼容接口） |
| 向量化 | all-MiniLM-L6-v2（本地 ONNX，384 维） |
| 检索 | SQL Server 2025 `VECTOR(384)` + `VECTOR_DISTANCE` · rank-bm25 · RRF |
| 存储 | SQL Server 2025（pyodbc） |

---

## 项目结构

```
project_1/
├── main.py               Web 入口（FastAPI + SSE）
├── config.py             全局配置
├── logging_config.py     日志（控制台 + 文件双输出）
├── agent/                预检 · 代码解析 · 风险评估 · 总结 · 编排图
├── tools/                代码读取与校验 / 记忆读写 / 三种检索策略
├── resources/            LLM · 向量化 · SQL Server 存储 · RAG 流水线
├── scripts/              建表 / 自检 / 性能观测 / 日志跟踪
├── static/index.html     前端页面
└── test_demo/            示例 C++ 代码
```

---

## 快速开始

**环境要求**：Python 3.10+、本地 SQL Server、ODBC Driver 17 for SQL Server

```bash
pip install -r requirements.txt
```

配置 `.env`：

```ini
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=sk-你的key
LLM_MODEL_NAME=deepseek-flash

SQLSERVER_DRIVER=ODBC Driver 17 for SQL Server
SQLSERVER_SERVER=localhost,1433
SQLSERVER_DATABASE=tech_debt_db
SQLSERVER_TRUSTED=yes
SQLSERVER_ENCRYPT=no
SQLSERVER_TRUST_CERT=yes

RETRIEVE_TOP_K=3
```

在「SQL Server 配置管理器」中启用 **TCP/IP**（端口 1433）并重启 SQL Server 服务，然后：

```bash
python scripts/init_sqlserver.py    # 建库建表
python main.py                      # 启动
```

浏览器打开 <http://127.0.0.1:8000>

---

## 核心设计

### 混合检索

```
查询文本
  ├─ 路①：算查询向量 → SQL Server VECTOR_DISTANCE 语义召回 top-N
  ├─ 路②：BM25 关键词召回 top-N
  └─ RRF 融合 → 最终 top-K
```

两路各召回 10 条候选，融合后取 top-3。

### 双层记忆

| | 存什么 | 怎么取 |
|---|--------|--------|
| **短期记忆** | `messages` 消息列表 | 按 `thread_id` 直接取（MemorySaver） |
| **长期记忆** | 结构化债务记录 + 向量 | 按相似度检索（SQL Server） |

长期记忆是一张表，同时承担三种检索：

```sql
dbo.debt_memory(
    file_path, risk_level, location, problem, suggestion,  -- 结构化字段 → 精确查询
    content,                                                -- 全文       → BM25
    embedding VECTOR(384),                                  -- 向量       → 语义检索
    create_time
)
```

写入方式为整体替换：每次分析后替换该文件的记录。

### 三层单向依赖

| 层 | 职责 |
|----|------|
| `agent/` | 定义"做什么"：Agent 与编排 |
| `tools/` | 定义"能怎么调"：把外部操作封装成工具 |
| `resources/` | 定义"有哪些能力"：LLM / 数据库 / 检索 |

---

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 返回前端页面 |
| `POST` | `/upload` | 上传代码，返回 `file_id` |
| `GET` | `/analyze` | SSE 流式分析，参数：`query` / `thread_id` / `file_id` |

SSE 事件顺序：

```
parse_result  →  risk_result  →  final_report  →  done
                                    出错时为 failed
```

---

*个人项目，用于学习*
