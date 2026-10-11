"""静态检查：找出项目里"定义了但没人引用"的东西。

用法：python scripts/dead_code_check.py

三层检查：
  ① 全项目零引用          —— 基本可确定是死代码
  ② 本文件没用到、也没被 import —— 更严格，能抓到"被同名掩盖"的情况
  ③ 未被引用的导入

原理很朴素：用 ast 扫出所有定义名，再扫出所有"被读到"的名字，两边一减。

已知误报源（需人工复核）：
  · 框架按约定调用：FastAPI 的 @app.get() 路由函数
  · 动态引用：getattr / 字符串里写函数名
  · 方法是通过"别的文件里的 obj.method()"调用的，所以只做全局检查
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_PARTS = {"__pycache__", "_backup", ".git", "logs"}
SELF = "dead_code_check.py"


def py_files():
    for p in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP_PARTS for part in p.parts):
            continue
        if p.name == SELF or p.name.startswith("_"):
            continue
        yield p


def collect(path: Path):
    """返回 (defs, imports, refs)

    defs    : [(name, lineno, kind, is_method)]
    imports : [(name, lineno)]
    refs    : {name}  —— 被"读"到的名字（赋值目标不算）
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defs, imports, refs = [], [], set()

    # ---------- 引用 & 导入 ----------
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if not isinstance(node.ctx, ast.Store):   # 只算读取
                refs.add(node.id)
        elif isinstance(node, ast.Attribute):
            refs.add(node.attr)
        elif isinstance(node, ast.Import):
            for a in node.names:
                imports.append(((a.asname or a.name).split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name != "*":
                    imports.append((a.asname or a.name, node.lineno))

    # ---------- 定义（区分方法 / 函数 / 常量）----------
    def walk_body(body, in_class, module_level):
        for node in body:
            if isinstance(node, ast.ClassDef):
                defs.append((node.name, node.lineno, "类", in_class))
                walk_body(node.body, True, False)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs.append((
                    node.name, node.lineno,
                    "方法" if in_class else "函数", in_class,
                ))
                walk_body(node.body, in_class, False)
            elif module_level and isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        defs.append((t.id, node.lineno, "常量", False))
            elif (module_level and isinstance(node, ast.AnnAssign)
                  and isinstance(node.target, ast.Name)):
                defs.append((node.target.id, node.lineno, "常量", False))

    walk_body(tree.body, False, True)
    return defs, imports, refs


def main():
    per_file = {}
    all_refs = set()
    imported = set()

    for f in py_files():
        defs, imports, refs = collect(f)
        per_file[f] = (defs, imports, refs)
        all_refs |= refs
        for name, _ in imports:
            imported.add(name)

    # ---------- 扫描范围 ----------
    total_defs = sum(len(d) for d, _i, _r in per_file.values())
    total_imp = sum(len(i) for _d, i, _r in per_file.values())
    print("=" * 78)
    print(f"扫描范围：{len(per_file)} 个 .py 文件 / "
          f"{total_defs} 个定义 / {total_imp} 处导入")
    print("=" * 78)

    # ---------- ① 全项目零引用 ----------
    print("【① 全项目都没提到（基本可确定是死代码）】")
    print("-" * 78)
    n1 = 0
    for f, (defs, _imp, _refs) in per_file.items():
        rel = f.relative_to(ROOT)
        for name, lineno, kind, _m in defs:
            if name.startswith("__") or name in all_refs:
                continue
            print(f"  {str(rel):<38} :{lineno:<4} [{kind}] {name}")
            n1 += 1
    if not n1:
        print("  （无）")

    # ---------- ② 本文件没用到、也没被 import ----------
    # 只对【模块级】定义做这层检查。
    # 方法不算：方法是通过别的文件里的 obj.method() 调用的，不走 import。
    print()
    print("=" * 78)
    print("【② 模块级定义：本文件没用、也没被任何文件 import】")
    print("-" * 78)
    n2 = 0
    for f, (defs, _imp, refs) in per_file.items():
        rel = f.relative_to(ROOT)
        for name, lineno, kind, is_method in defs:
            if is_method or name.startswith("__"):
                continue
            if name in refs or name in imported:
                continue
            print(f"  {str(rel):<38} :{lineno:<4} [{kind}] {name}")
            n2 += 1
    if not n2:
        print("  （无）")

    # ---------- ③ 未被引用的导入 ----------
    print()
    print("=" * 78)
    print("【③ 未被引用的导入】")
    print("-" * 78)
    n3 = 0
    for f, (_defs, imports, refs) in per_file.items():
        rel = f.relative_to(ROOT)
        for name, lineno in imports:
            if name.startswith("__") or name in refs:
                continue
            print(f"  {str(rel):<38} :{lineno:<4} {name}")
            n3 += 1
    if not n3:
        print("  （无）")

    print()
    print("=" * 78)
    print(f"合计：① {n1} 个，② {n2} 个，③ {n3} 个")
    print("静态扫描有误报，请人工复核后再删。")
    print("=" * 78)


if __name__ == "__main__":
    main()
