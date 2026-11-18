#!/usr/bin/env python3
"""Intent: turn one of the native renderer programs (a main() that reads command lines from stdin until the end) into a module a page can drive: `vu_init()` runs what main did before
its loop, `vu_cmd(line)` runs the loop body once for one command line, `vu_fb()` returns the RGB565 frame buffer. The original files are not edited: this reads one and writes a
copy to another folder. The command set, the drawing and the output lines stay exactly the program's own.
Usage: shim_main.py SRC.cc DST.cc
Every replacement must match exactly once; a changed source stops the build with a message (update CONTINUES below, or the program was rewritten).
Placement: host-side development tool. Upstream: none."""
import re
import sys
from pathlib import Path

LOOP = "while (std::getline(std::cin, line)) {"
# loop-level `continue;` statements (not the ones inside a for loop in a command), by file name; each becomes `return;`
CONTINUES = {
    "render.cc": ["if (c.empty() || c[0] == '#') continue;", "fprintf(stderr, \"unknown overlay %s\\n\", n.c_str()); continue;"],
    "lock_render.cc": [],
    "cover_render.cc": [],
}
DECL = re.compile(r"^    (?!static )(bool|int|int64_t|double|float|std::string|lv_display_t\*|lv_indev_t\*|auto)\s")


def fail(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 1


def main() -> int:
    if len(sys.argv) != 3:
        return fail("Usage: shim_main.py SRC.cc DST.cc. Give the native renderer source and where to write the browser copy.")
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    text = src.read_text()
    m = re.search(r"^int main\(\)\s*\n\{\n", text, re.M)
    if not m or text.count(LOOP) != 1:
        return fail(f"{src.name}: no `int main()` with a stdin command loop. The program changed: update scripts/virtual-unit/wasm/shim_main.py for it.")
    head = text[: m.start()]
    rest = text[m.end():]
    init, after = rest.split("    " + LOOP, 1)
    # the loop body ends at the closing brace that matches the loop's opening one
    depth, i = 1, 0
    while depth:
        c = after[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    body = after[: i - 1]
    for pat in CONTINUES.get(src.name, []):
        if body.count(pat) != 1:
            return fail(f"{src.name}: expected `{pat}` once in the command loop. Update CONTINUES in scripts/virtual-unit/wasm/shim_main.py.")
        body = body.replace(pat, pat.replace("continue;", "return;"))
    init_lines = []
    for line in init.splitlines():
        if line.strip() == "std::string line;":
            continue
        init_lines.append("    static " + line[4:] if DECL.match(line) else line)
    out = head + "\n// ---- browser entry points (scripts/virtual-unit/wasm/shim_main.py): main() split into init and one command ----\n"
    out += "#include <functional>\n#include <emscripten.h>\n"
    out += "static std::function<void(const std::string&)> g_vu_step;\n"
    out += 'extern "C" EMSCRIPTEN_KEEPALIVE void vu_init()\n{\n' + "\n".join(init_lines) + "\n"
    out += "    g_vu_step = [](const std::string& line) {" + body + "};\n}\n"
    out += 'extern "C" EMSCRIPTEN_KEEPALIVE void vu_cmd(const char* l) { g_vu_step(std::string(l)); fflush(stdout); }\n'
    out += 'extern "C" EMSCRIPTEN_KEEPALIVE const uint8_t* vu_fb() { return s_buf; }\n'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(out)
    print(f"{src.name}: {len(init_lines)} init lines, {body.count(chr(10))} loop lines -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
