# main.py
import json
import logging
import traceback
import uuid

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from agent.graph import build_graph
from logging_config import setup_logging
from tools.code_tools import validate_upload

LOG_FILE = setup_logging()          # 控制台 + 文件双输出
logging.getLogger(__name__).info("日志文件：%s", LOG_FILE)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# 底层资源（LLM / 向量库 / SQL Server / RAG）在 resources/ 里已初始化好，
# 工具层封装在 tools/，Agent 层直接用；这里只负责「编排 + 对外提供 Web 接口」
graph = build_graph(checkpointer=MemorySaver())  # 短期记忆：按 thread_id 存多轮对话状态

# 用户上传的代码暂存（内存，演示用；重启即清空）
uploaded_code = {}


class UploadPayload(BaseModel):
    file_name: str = "uploaded.cpp"
    code_content: str = ""


@app.get("/")
async def index():
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")


@app.post("/upload")
async def upload_code(payload: UploadPayload):
    """接收前端上传的代码文件，返回 file_id 供后续 /analyze 使用。

    在这里就把非代码文件挡掉 —— 避免它们白白消耗大模型调用，
    也避免把无关内容写进长期记忆（记忆污染）。
    """
    file_name = payload.file_name.strip() or "uploaded.cpp"
    code = payload.code_content or ""

    ok, reason = validate_upload(file_name, code)
    if not ok:
        logging.warning("上传被拒绝：%s（文件：%s）", reason, file_name)
        return {"error": reason}

    file_id = uuid.uuid4().hex[:12]
    uploaded_code[file_id] = {"file_name": file_name, "code_content": code}
    logging.info("已接收上传：%s（%d 字符）", file_name, len(code))
    return {"file_id": file_id, "file_name": file_name}


@app.get("/analyze")
async def analyze(query: str = "分析这个C++代码的技术债务", thread_id: str = "default", file_id: str = ""):
    try:
        # 优先使用用户上传的代码；未上传则默认分析 test_demo/main.cpp
        file_name = "main.cpp"
        code_content = ""
        if file_id and file_id in uploaded_code:
            file_name = uploaded_code[file_id]["file_name"]
            code_content = uploaded_code[file_id]["code_content"]

        input_state = {
            "user_query": query,
            "code_content": code_content,   # 为空时由代码解析Agent通过 scan_code_tool 读取
            "file_name": file_name,
            "parse_result": "",
            "risk_result": "",
            "final_report": "",
            "messages": [HumanMessage(content=query)],  # 结构化消息列表（短期记忆）
            "debt_items": []                            # 结构化债务记录（长期记忆）
        }
        config = {"configurable": {"thread_id": thread_id}}
        stream = graph.stream(input_state, config=config)
    except Exception as e:
        logging.error("分析初始化失败: %s\n%s", e, traceback.format_exc())

        async def init_error_gen():
            yield {"event": "failed", "data": json.dumps(str(e), ensure_ascii=False)}
            yield {"event": "done", "data": "done"}

        return EventSourceResponse(init_error_gen())

    async def event_generator():
        # 只推送前端需要的文本字段；messages 里是 AIMessage 等对象，不能 JSON 序列化，必须跳过
        display_keys = ("parse_result", "risk_result", "final_report")
        try:
            for s in stream:
                for node_name, val in s.items():
                    if not isinstance(val, dict):
                        continue
                    for key in display_keys:
                        if key in val:
                            yield {
                                "event": key,
                                "data": json.dumps(val[key] or "", ensure_ascii=False, default=str),
                            }
            yield {"event": "done", "data": "done"}
        except Exception as e:
            logging.error("分析执行失败: %s\n%s", e, traceback.format_exc())
            yield {"event": "failed", "data": json.dumps(str(e), ensure_ascii=False)}
            yield {"event": "done", "data": "done"}

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn
    # log_config=None：不让 uvicorn 覆盖我们的日志配置
    uvicorn.run("main:app", host="127.0.0.1", port=8000, log_config=None)
