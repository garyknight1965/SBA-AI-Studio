\
"""
SBA AI Studio - Import Graph
AS-004

Read-only import dependency analyzer.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

IGNORE={".git","__pycache__",".venv",".venv310",".venv312","logs","archive"}

def skip(p:Path)->bool:
    return any(part in IGNORE for part in p.parts)

def pyfiles(root:Path):
    return [p for p in root.rglob("*.py") if not skip(p)]

def imports_for(path:Path):
    try:
        tree=ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    found=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            found.extend(a.name for a in node.names)
        elif isinstance(node,ast.ImportFrom):
            mod=node.module or ""
            found.append(mod)
    return sorted(set(found))

def main():
    root=Path.cwd()
    files=pyfiles(root)

    imports=defaultdict(list)
    imported_by=defaultdict(list)

    rels={f:f.relative_to(root).as_posix() for f in files}

    for f in files:
        src=rels[f]
        for imp in imports_for(f):
            imports[src].append(imp)
            token=imp.replace(".","/")
            for other in files:
                rel=rels[other]
                if rel.endswith(token+".py") or rel.endswith(token+"/__init__.py"):
                    imported_by[rel].append(src)

    print("="*72)
    print("SBA AI Studio - Import Graph")
    print("="*72)

    orphan=0
    for rel in sorted(rels.values()):
        users=sorted(set(imported_by.get(rel,[])))
        if not users and not rel.endswith(("start.py","app.py")):
            orphan+=1
            print(f"\nORPHAN: {rel}")
        else:
            print(f"\nFILE: {rel}")
        print("Imported by:")
        if users:
            for u in users:
                print("  -",u)
        else:
            print("  (none)")
    print("\n"+"="*72)
    print(f"Potential orphan files: {orphan}")
    print("No files were modified.")

if __name__=="__main__":
    main()
