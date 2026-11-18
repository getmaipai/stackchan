#!/usr/bin/env python3
"""Intent: list every task a replayed firmware tree creates with a stack in internal RAM (xTaskCreate and xTaskCreatePinnedToCore, not the WithCaps forms),
with its name, stack size and source line, largest first: the static half of the question what splits the internal heap. Usage: internal-tasks.py TREE
where TREE is a fw-rebuild.sh tree (it reads TREE/firmware). Placement: host-side development tool; no firmware change. Upstream: none."""
import re
import sys
from pathlib import Path

CALL = re.compile(r'xTaskCreate(?:Pinned(?:ToCore)?)?\s*\(')
rows = []
root = Path(sys.argv[1]) / "firmware"
for sub in ("main", "xiaozhi-esp32/main", "managed_components"):
    for path in (root / sub).rglob("*"):
        if path.suffix not in (".c", ".cc", ".cpp"):
            continue
        rel = str(path.relative_to(root))
        # only code this firmware builds: not the test apps and demo applications of the managed components, not the other boards of the base tree
        if any(x in rel for x in ("/test", "test_app", "/applications/", "/examples/", "/boards/")) and "/boards/common/" not in rel:
            continue
        text = path.read_text(errors="replace")
        for m in CALL.finditer(text):
            args = text[m.end(): m.end() + 700]
            # the name is the first string literal; the stack is the argument after it (a number, an expression or a named constant)
            n = re.search(r'"([^"]+)"\s*,\s*([^,]+),', args)
            if not n:
                continue
            line = text.count("\n", 0, m.start()) + 1
            rows.append((n.group(1), n.group(2).strip(), f"{path.relative_to(root)}:{line}"))

def size(expr: str) -> int:
    try:
        return int(eval(expr.replace("*", " * "), {"__builtins__": {}}, {}))
    except Exception:
        return -1

rows.sort(key=lambda r: -size(r[1]))
print("| Task | Stack (bytes or the expression) | Where |\n|---|---|---|")
for name, stack, where in rows:
    print(f"| {name} | {size(stack) if size(stack) >= 0 else stack} | `{where}` |")
