# 技术债务多 Agent 分析系统

> 基于 **LangGraph 多 Agent 协作** + **混合检索 RAG** 的 C++ 代码技术债务分析工具。
> 在网页上提问，系统自动调度 3 个 Agent 依次完成「代码解析 → 风险评估 → 总结报告」，
> 并把分析结果沉淀为**可复用的长期记忆**。

---

## 目录

- [一、项目简介](#一项目简介)
- [二、功能特性](#二功能特性)
- [三、系统架构](#三系统架构)
- [四、技术栈](#四技术栈)
- [五、项目结构](#五项目结构)
- [六、快速开始](#六快速开始)
- [七、核心设计](#七核心设计)
- [八、API 接口](#八api-接口)

---

## 一、项目简介

传统代码审查依赖人工，效率低且经验难以沉淀。本项目用 **多 Agent 协作 + RAG 记忆**
把这个过程自动化：

1. **代码解析 Agent** 读懂源码，提取函数清单、代码异味、债务线索
2. **风险评估 Agent** 结合历史记忆判断风险等级（高/中/低），给出原因和修复建议
3. **总结 Agent** 汇总成结构化报告，并**写回长期记忆**

下次分析类似代码时，风险评估 Agent 会**自动召回历史记录**，实现"越用越懂你的项目"。

---

## 二、功能特性

| 特性 | 说明 |
|------|------|
| 🤖 **多 Agent 协作** | LangGraph 状态图编排 3 个专职 Agent |
| 🔍 **混合检索 RAG** | 向量语义检索 + BM25 关键词检索 + RRF 融合 |
| 🧠 **双层记忆系统** | 短期（多轮对话）+ 长期（结构化债务记录） |
| 💬 **聊天式交互** | SSE 流式输出，逐字打字机 + Markdown 渲染 |
| 📎 **代码上传** | 支持上传自己的 C/C++ 文件分析，或使用内置示例 |
| 🔀 **线程隔离** | 按 `thread_id` 区分会话，多轮对话互不干扰 |
| 🗄️ **单库存储** | SQL Server 2025（结构化字段 + 原生 `VECTOR(384)` 向量） |

---

## 三、系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  ① 浏览器   static/index.html                                │
│     聊天界面 · Markdown 渲染 · 文件上传 · 会话 thread_id       │
└───────────────────────────┬─────────────────────────────────┘
                            │  ① POST /upload
                            │  ② GET  /analyze  (SSE 流)
┌───────────────────────────▼─────────────────────────────────┐
│  ② Web 层   main.py                                          │
│     FastAPI + Uvicorn + sse-starlette                        │
│     收请求 → 组装状态 → graph.stream() → 流式推回前端          │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  ③ Agent 核心层   agent/                                     │
│                                                              │
│    START ──► ①代码解析 ──► ②风险评估 ──► ③总结报告 ──► END   │
│                  │             │              │              │
│                  │             │              └─ 写记忆       │
│                  │             └─ 查记忆（RAG）               │
│                  └─ 读代码                                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  ④ 工具层   tools/                                           │
│     code_tools       读代码                                   │
│     memory_tools     写记忆 / 查结构化历史                    │
│     retrieval_tools  3 种检索策略（可扩展）                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  ⑤ 底层资源层   resources/                                    │
│     llm.py              LLM 实例                             │
│     embedding.py        文本向量化（all-MiniLM-L6-v2）        │
│     sqlserver_store.py  SQL Server（结构化字段 + VECTOR 向量）│
│     rag_pipeline.py     BM25 + RRF 混合检索流水线              │
└─────────────────────────────────────────────────────────────┘

依赖方向严格单向：  resources  ←  tools  ←  agent  ←  main
```

---

## 四、技术栈

### 前端
| 技术 | 用途 |
|------|------|
| 原生 HTML / CSS / JavaScript | 无框架，聊天式 UI |
| SSE (EventSource) | 流式接收各 Agent 输出 |
| FileReader | 读取本地文件上传 |
| localStorage | 保存会话 `thread_id` |

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.115.6 | Web 框架 |
| Uvicorn | 0.32.0 | ASGI 服务器 |
| sse-starlette | 2.1.3 | SSE 流式输出 |
| Pydantic | 2.9.2 | 数据校验 |

### Agent 编排
| 技术 | 版本 | 用途 |
|------|------|------|
| LangGraph | 0.2.40 | 状态图多 Agent 编排 |
| LangChain | 0.3.7 | LLM 抽象层 |
| langchain-core | — | 消息类型、`@tool`、`add_messages` reducer |

### LLM
| 技术 | 说明 |
|------|------|
| DeepSeek `deepseek-flash` | OpenAI 兼容接口 |
| langchain-openai | 0.2.11 |

### 检索 / 存储
| 技术 | 版本 | 用途 |
|------|------|------|
| SQL Server 2025 | — | 结构化字段 + 原生 `VECTOR(384)` 向量 |
| VECTOR_DISTANCE | — | 余弦距离精确 kNN 语义检索（正式版功能） |
| all-MiniLM-L6-v2 | 内置 | 本地 Embedding（384 维，ONNX） |
| rank-bm25 | 0.2.2 | BM25 稀疏检索（Python 侧计算） |
| RRF | 手写 | 倒数排名融合 |
| pyodbc | 5.x | SQL Server 驱动 |

---

## 五、项目结构

```
project_1/
├── main.py                      Web 入口（FastAPI + SSE）
├── config.py                    全局配置（读 .env）
├── logging_config.py            日志配置（控制台 + 文件）
├── .env                         密钥与连接配置
├── requirements.txt
│
├── agent/                       【Agent 核心层】
│   ├── state.py                 状态定义（黑板）
│   ├── prompts.py               3 个 Agent 的提示词
│   ├── precheck.py              ⓪ 预检节点（非代码直接短路）
│   ├── code_parser_agent.py     ① 代码解析 Agent
│   ├── risk_agent.py            ② 风险评估 Agent（自主调用检索工具）
│   ├── summary_agent.py         ③ 总结 Agent（覆盖式写入记忆）
│   └── graph.py                 编排图
│
├── tools/                       【工具层】
│   ├── code_tools.py            代码读取 + 上传校验
│   ├── memory_tools.py          记忆写入 / 查询
│   └── retrieval_tools.py       检索策略（3 种，可扩展）
│
├── resources/                   【底层资源层】
│   ├── llm.py                   LLM 实例
│   ├── embedding.py             文本向量化
│   ├── sqlserver_store.py       SQL Server（结构化 + 向量）
│   └── rag_pipeline.py          BM25 + RRF 检索流水线
│
├── docs/                        项目文档
│   ├── 问题记录.md              13 个踩坑与解决
│   ├── 向量与切分说明.md         RAG 原理（向量怎么算 / 为什么不用切分）
│   ├── 文件组织与依赖关系.md     目录为什么这么分、文件怎么联系
│   ├── 术语表.md                名词解释（可长期追加）
│   └── 面试题精讲.md            检索层三问（RRF / 余弦距离 / 向量索引）
│
├── scripts/                     初始化 / 自检 / 维护脚本
│   ├── init_sqlserver.py        建库 + 建表
│   ├── clean_memory.py          查看 / 清理长期记忆
│   ├── test_db_write.py         连通性 + 去重自检
│   ├── test_dedup.py            批内去重逻辑测试（不需要数据库）
│   ├── test_upload_check.py     上传校验测试（不需要数据库）
│   ├── bench.py                 各部分耗时观测
│   ├── tail_log.py              实时跟踪日志
│   └── show_tool_schema.py      展示发给模型的工具 JSON Schema
│
├── logs/                        运行日志（app.log，超 5MB 自动切割）
├── static/index.html            前端页面
└── test_demo/                   示例 C++ 代码
```

---

## 六、快速开始

### 1. 环境要求

- **Python 3.10+**
- **SQL Server**（本地实例，用于结构化长期记忆）
- **ODBC Driver 17 for SQL Server**

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 `.env`

把 `.env` 里的密钥换成你自己的：

```ini
# ===== LLM =====
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=sk-你的key
LLM_MODEL_NAME=deepseek-flash

# ===== SQL Server（长期记忆：结构化字段 + 向量）=====
SQLSERVER_DRIVER=ODBC Driver 17 for SQL Server
SQLSERVER_SERVER=localhost,1433
SQLSERVER_DATABASE=tech_debt_db
SQLSERVER_TRUSTED=yes          # Windows 身份验证
SQLSERVER_ENCRYPT=no
SQLSERVER_TRUST_CERT=yes

# ===== 检索 =====
RETRIEVE_TOP_K=3
```

### 4. 准备 SQL Server

**① 启用 TCP/IP**

打开「SQL Server 配置管理器」→ SQL Server 网络配置 → `MSSQLSERVER 的协议`
→ 启用 **TCP/IP** → IPAll 的 **TCP 端口 = 1433** → **重启 SQL Server 服务**

**② 建库建表**

```bash
python scripts/init_sqlserver.py
```

预期输出：
```
① 连接 master ...
   数据库 [tech_debt_db] 已就绪
② 连接 [tech_debt_db] 建表 ...
   表 dbo.debt_memory 已就绪 ✅
```

### 5. 启动

```bash
python main.py
```

浏览器打开 **http://127.0.0.1:8000**

### 6. 使用

1. 输入问题，或点快捷标签
2. 也可以点 **📎** 上传自己的 C/C++ 文件
3. 观察 3 个 Agent 依次回复（顶部的流程条会实时高亮）

---

## 七、核心设计

### 7.1 三层架构

| 层 | 职责 | 规则 |
|----|------|------|
| **Agent 核心层** | 定义"做什么"：3 个 Agent + 编排 | 可依赖工具层、资源层 |
| **工具层** | 定义"能怎么调"：把能力封装成工具 | 只能依赖资源层 |
| **底层资源层** | 定义"有哪些能力"：LLM / 数据库 / 检索 | 只依赖 config |

**依赖方向严格单向**：`resources ← tools ← agent ← main`

好处：
- 换存储（SQLite → SQL Server）只改资源层 + 工具层一行 import
- 加检索策略只改工具层一个文件
- Agent 编排逻辑完全不受底层变化影响

### 7.2 多 Agent 编排（LangGraph）

```python
builder.add_node("code_parser", code_parser_node)
builder.add_node("risk_agent", risk_agent_node)
builder.add_node("summary_agent", summary_agent_node)

builder.add_edge(START, "code_parser")
builder.add_edge("code_parser", "risk_agent")
builder.add_edge("risk_agent", "summary_agent")
builder.add_edge("summary_agent", END)
```

**关键机制**：
- **节点**：读全量状态 → 只返回要改的字段，框架自动合并
- **Reducer**：`messages` 用 `add_messages`（追加），其他字段默认覆盖
- **Checkpointer**：`MemorySaver` 按 `thread_id` 存档，实现多轮记忆

### 7.3 混合检索 RAG

```
查询文本
  ├─ 路①：all-MiniLM-L6-v2 算向量 → SQL Server `VECTOR_DISTANCE` 语义召回 top-N
  ├─ 路②：BM25 关键词召回 top-N（只保留 score > 0）
  └─ RRF 融合 → 最终 top-K
```

**为什么混合？**

| 查询类型 | 向量 | BM25 |
|---------|------|------|
| `内存安全问题`（语义） | ✅ 命中 | ❌ 全 0 |
| `global_buf`（精确标识符） | 一般 | ✅ 精准 |

两者互补，所以用 **RRF（倒数排名融合）** 合并：

```
score(d) = Σ 1 / (k + rank_i(d))      # k 常取 60
```

### 7.4 双层记忆系统

```
┌──────────────────────────────────────────────────────┐
│  短期记忆（本次对话）                                  │
│  · messages 列表：HumanMessage / AIMessage            │
│  · 存于 MemorySaver（内存）                            │
│  · 按 thread_id 区分会话                              │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  长期记忆（跨会话永久保存）→ 全在 SQL Server 一张表    │
│                                                       │
│  表 dbo.debt_memory(                                  │
│    file_path, risk_level, location,                   │
│    problem, suggestion,      ← 结构化字段（精确查询）  │
│    content,                  ← 全文（BM25 检索）       │
│    embedding VECTOR(384),    ← 向量（语义检索）        │
│    create_time )                                      │
└──────────────────────────────────────────────────────┘
```

---

## 八、API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 返回前端页面 |
| `POST` | `/upload` | 上传代码文件，返回 `file_id` |
| `GET` | `/analyze` | SSE 流式分析 |

### `POST /upload`

```json
// 请求
{ "file_name": "main.cpp", "code_content": "..." }

// 响应
{ "file_id": "a1b2c3d4e5f6", "file_name": "main.cpp" }
```

### `GET /analyze`

| 参数 | 说明 |
|------|------|
| `query` | 用户问题 |
| `thread_id` | 会话 ID（区分多轮对话） |
| `file_id` | 上传文件的 ID（不传则分析内置示例） |

**SSE 事件**：

| 事件 | 内容 |
|------|------|
| `parse_result` | 代码解析结果 |
| `risk_result` | 风险评估结果 |
| `final_report` | 总结报告 |
| `failed` | 错误信息 |
| `done` | 结束标记 |

---

## 附：项目亮点（答辩要点）

1. **混合检索 RAG** —— 向量（语义）+ BM25（关键词）+ RRF 融合，
   实测验证了"语义查询向量更强、精确标识符 BM25 更强"

2. **单库架构（SQL Server 2025）** —— 结构化字段、全文、`VECTOR(384)` 向量
   存在同一张表里；用原生 `VECTOR_DISTANCE` 做余弦语义检索，**不需要额外向量数据库**

3. **双层记忆架构** —— 短期（消息列表 + checkpointer）+ 长期（SQL Server 单表），
   实现"越用越懂你的项目"

4. **三层单向依赖架构** —— Agent / 工具 / 资源彻底解耦；
   底层从「ChromaDB + SQLite 双库」迁到「SQL Server 单库」，**上层零改动**

4. **工具化封装** —— 所有外部操作收口到 `tools/`，
   检索策略可插拔扩展

---

*本项目为学习/演示用途，生产环境请补充鉴权、限流、错误重试等机制。*
