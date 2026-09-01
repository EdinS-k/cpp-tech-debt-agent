"""工具层：把底层能力封装成 Agent 可调用的工具。

· 代码读取 / 上传校验 → code_tools
· 长期记忆           → memory_tools
· 检索策略           → retrieval_tools（可自由增加多个，Agent 按需选用）

注意：这里**故意不做 re-export**。
  如果用 `from tools.code_tools import xxx`，Python 会先执行本文件；
  一旦本文件 import 了 memory_tools，就会连带加载 resources.sqlserver_store
  → 连数据库、加载 embedding 模型。
  结果：想用个纯本地函数，却被迫连上整个存储栈（也让单元测试没法单独跑）。

  所以各模块请直接 import 子模块：
      from tools.code_tools import validate_upload      ✅
      from tools import validate_upload                 ❌
"""
