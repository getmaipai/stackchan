"""The Wi-Fi setup portal (firmware patches P01 to P04): its page, string table, routes and plain-C core.

No unit is needed: the page and the core come out of the patches, the core is built and run with the host C
compiler, and the page is served by a local HTTP server exactly as the unit assembles it (page text with the
marker swapped for the chosen language's 15-string table).
"""

from __future__ import annotations

import http.server
import json
import re
import shutil
import subprocess
import threading
import urllib.request
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PATCHES = HERE.parent.parent / "firmware" / "patches"
C_TEST = HERE / "firmware" / "portal_core_test.c"

PORTAL_PATCHES = [
    "P01-portal-page.patch",
    "P02-portal-routes.patch",
    "P03-portal-protect.patch",
    "P04-portal-language.patch",
]
MARKER = "@T@"
SLOTS = 15
PAGE_BUDGET = 5 * 1024  # the design: about 4 to 5 KB, English or Spanish


def added_file(patch: str, path: str) -> str:
    """The text of a new file a patch adds."""
    text = (PATCHES / patch).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1]
    body = block.split("\n", 1)[1]  # drop the @@ line
    lines = []
    for line in body.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


@pytest.fixture(scope="module")
def sources(tmp_path_factory):
    """The new files of the portal as plain files, taken from the patches."""
    d = tmp_path_factory.mktemp("portal")
    (d / "maipai_portal_core.h").write_text(added_file(PORTAL_PATCHES[0], "firmware/portal/maipai_portal_core.h"))
    (d / "maipai_portal_page.h").write_text(added_file(PORTAL_PATCHES[0], "firmware/portal/maipai_portal_page.h"))
    return d


@pytest.fixture(scope="module")
def core_binary(sources, tmp_path_factory):
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    binary = sources / "portal_core_test"
    build = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{sources}", str(C_TEST), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    return binary


def test_core_c_tests_pass(core_binary):
    run = subprocess.run([str(core_binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout


def table(core_binary, lang: str) -> list[str]:
    out = subprocess.run([str(core_binary), "table", lang], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def test_string_table_is_complete_in_both_languages(core_binary):
    en, es = table(core_binary, "en"), table(core_binary, "es")
    assert len(en) == len(es) == SLOTS
    assert all(s.strip() for s in en + es)
    assert all(a != b for a, b in zip(en, es))
    assert any(ch in "".join(es) for ch in "áéíóúñ"), "Spanish text must carry its accents"
    for s in en + es:
        assert chr(0x2014) not in s, "no em dashes"
    # every error says what went wrong and what to do: the error slots end in an instruction or a way forward
    assert "Check" in en[14] and "Revise" in es[14]
    assert "code" in en[12].lower() and "código" in es[12].lower()


def render(sources: Path, core_binary, lang: str) -> bytes:
    page = re.search(r'R"MPHTML\((.*)\)MPHTML"', (sources / "maipai_portal_page.h").read_text(), re.S).group(1)
    assert page.count(MARKER) == 1
    return page.replace(MARKER, subprocess.run([str(core_binary), "table", lang], capture_output=True, text=True).stdout).encode()


def test_page_is_one_small_self_contained_file(sources, core_binary):
    for lang in ("en", "es"):
        body = render(sources, core_binary, lang)
        assert 2500 < len(body) <= PAGE_BUDGET, f"{lang} page is {len(body)} bytes"
        text = body.decode()
        assert re.search(r"(src|href|action)=[\"']?https?:", text) is None, "no outside address"
        assert "<link" not in text and "<img" not in text and "@import" not in text and "url(" not in text
        assert "prefers-color-scheme:dark" in text, "dark mode by browser setting"
        assert 'name=viewport' in text
        assert "/scan" in text and "/submit" in text
        # large touch targets: 48 px or more on the inputs and list rows
        assert text.count("min-height:48px") >= 2 and "min-height:52px" in text


def test_page_uses_every_string_slot_the_server_does_not(sources, core_binary):
    page = (sources / "maipai_portal_page.h").read_text()
    used = {int(n) for n in re.findall(r"data-t=(\d+)", page)} | {int(n) for n in re.findall(r"T\[(\d+)\]", page)}
    used |= {int(n) for n in re.findall(r"say\((\d+)", page)} | {int(n) for n in re.findall(r"\?(\d+):", page)}
    # slots the server answers with in "e" (BADCODE, LOCKED, FAIL, BADHOST) reach the page through say(r.e)
    server_slots = {4, 12, 13, 14}
    assert used | server_slots == set(range(SLOTS))
    assert max(used) < SLOTS


def test_page_served_over_http_like_the_unit_does(sources, core_binary):
    body = render(sources, core_binary, "es")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path.split("?")[0] == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(302)
                self.send_header("Location", "http://192.168.4.1/")
                self.end_headers()

        def log_message(self, *a):  # silence
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_port}/?x=1", timeout=5) as r:
            got = r.read()
            assert r.status == 200 and "text/html" in r.headers["Content-Type"]
        assert got == body and len(got) <= PAGE_BUDGET
        assert "Configurar StackChan".encode() in got
    finally:
        srv.shutdown()


# ---- routes, protection and wiring, read from the patches ----

CAPTIVE_PROBES = [
    "/hotspot-detect.html",  # Apple
    "/library/test/success.html",  # Apple
    "/generate_204",  # Android
    "/gen_204",  # Android
    "/mobile/status.php",  # Android
    "/connecttest.txt",  # Windows
    "/ncsi.txt",  # Windows
    "/check_network_status.txt",  # Windows
    "/fwlink/",  # Windows
    "/redirect",  # Windows
    "/canonical.html",  # Firefox
    "/success.txt",  # Firefox
    "/connectivity-check.html",  # various
    "/favicon.ico",
    "/anything/else?x=1",
]


def routes(source: str) -> list[tuple[str, str]]:
    found = re.findall(r'\.uri = "([^"]+)",\s*\.method = HTTP_(GET|POST)', source)
    return [(m, u) for u, m in found]


def wildcard_match(template: str, uri: str) -> bool:
    """The unit's matcher is httpd_uri_match_wildcard: a trailing * matches everything, a query is ignored."""
    path = uri.split("?")[0].split("#")[0]
    if template.endswith("*"):
        return path.startswith(template[:-1])
    return path == template


def test_routes_are_the_four_the_design_keeps():
    src = added_file("P02-portal-routes.patch", "firmware/portal/maipai_wifi_configuration_ap.cc")
    assert routes(src) == [("GET", "/"), ("GET", "/scan"), ("POST", "/submit"), ("GET", "/*")]
    handlers = src.count("httpd_register_uri_handler(")
    assert handlers == 4  # was 24 in the component (the design says about 8)
    assert re.search(r"max_uri_handlers = ([0-9]+)", src).group(1) == "8"
    # the catch-all is registered last, so the three real routes win
    order = [m.start() for m in re.finditer(r"httpd_register_uri_handler\(server_, &(\w+)\)", src)]
    names = re.findall(r"httpd_register_uri_handler\(server_, &(\w+)\)", src)
    assert names == ["page", "scan", "submit", "catch_all"] and order == sorted(order)
    # no advanced, saved-network, exit or done routes; no saved network names anywhere
    for gone in ("/saved", "/advanced", "/exit", "/done.html", "GetSsidList", "ssid_list", "ota_url"):
        assert gone not in src, gone


def test_every_phone_and_pc_probe_reaches_the_redirect():
    src = added_file("P02-portal-routes.patch", "firmware/portal/maipai_wifi_configuration_ap.cc")
    table = routes(src)
    for probe in CAPTIVE_PROBES:
        hits = [uri for method, uri in table if method == "GET" and wildcard_match(uri, probe)]
        assert hits[0] == "/*", f"{probe} matched {hits}"  # first match wins on the unit: only the catch-all
    assert wildcard_match("/", "/?lang=es") and not wildcard_match("/", "/x")
    assert '"302 Found"' in src and "http://192.168.4.1/" in src


def test_protection_is_in_p03():
    p03 = (PATCHES / "P03-portal-protect.patch").read_text()
    added = "\n".join(line for line in p03.splitlines() if line.startswith("+"))
    for needed in (
        "mp_guard_check",  # the setup code gates /submit
        "mp_code_make(esp_random()",  # a fresh code per window
        "MP_PORTAL_WINDOW_S",  # the timeout
        "mp_ssid(",  # the generic hex hotspot name
        "maipai_portal_active",  # the screen shows the hint although captions are off
        "memset(s_code",  # the code is cleared when setup ends
    ):
        assert needed in added, needed
    core = added_file("P01-portal-page.patch", "firmware/portal/maipai_portal_core.h")
    window = int(re.search(r"#define MP_PORTAL_WINDOW_S (\d+)", core).group(1))
    assert 300 <= window <= 600, "the window is 5 to 10 minutes"
    assert int(re.search(r"#define MP_PORTAL_MAX_BAD_CODES (\d+)", core).group(1)) <= 5


def test_stop_frees_everything_it_started():
    p03 = (PATCHES / "P03-portal-protect.patch").read_text()
    p02 = added_file("P02-portal-routes.patch", "firmware/portal/maipai_wifi_configuration_ap.cc")
    stop = p02.split("void WifiConfigurationAp::Stop()", 1)[1]
    for freed in ("httpd_stop(server_)", "dns_server_->Stop()", "dns_server_.reset()", "esp_timer_delete(scan_timer_)",
                  ".swap(ap_records_)", "esp_netif_destroy_default_wifi"):
        assert freed in stop, freed
    assert "esp_timer_delete(s_window_timer)" in p03


def test_every_patch_carries_its_header_lines_and_is_in_order():
    order = (PATCHES / "ORDER").read_text().split()
    last = order.index(PORTAL_PATCHES[0])
    assert order[last : last + len(PORTAL_PATCHES)] == PORTAL_PATCHES or all(p in order for p in PORTAL_PATCHES)
    for name in PORTAL_PATCHES + ["P05-portal-wire.patch"]:
        head = "\n".join((PATCHES / name).read_text().splitlines()[:8])
        for tag in ("# Intent:", "# Placement: unit (", "# Upstream:"):
            assert tag in head, f"{name} has no {tag}"
        assert "\u2014" not in (PATCHES / name).read_text()


def test_p05_turns_the_portal_on_and_off_by_one_switch():
    p05 = (PATCHES / "P05-portal-wire.patch").read_text()
    assert "config MAIPAI_WIFI_PORTAL" in p05 and "default y" in p05
    assert "if(NOT CONFIG_MAIPAI_WIFI_PORTAL)" in p05  # the source swap follows the switch
    assert "#if CONFIG_MAIPAI_WIFI_PORTAL" in p05  # board and network wait follow the switch
    assert "requestAppSetup" in p05  # the switch off keeps the old path
    # the portal never leaves the setup wait by restarting while it is open
    assert "give_up = false;" in p05
