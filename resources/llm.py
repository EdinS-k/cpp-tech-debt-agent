# resources/llm.py
"""底层资源层：初始化好的 LLM 实例（DeepSeek，OpenAI 兼容接口）。

全项目共用这一个实例，避免到处重复创建。
"""
from langchain_openai import ChatOpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME

llm = ChatOpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    model=LLM_MODEL_NAME,
)
