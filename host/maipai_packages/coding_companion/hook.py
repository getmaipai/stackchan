"""A hook a coding agent runs to tell the robot its state. It sends the state, the kind and the project name, and nothing else.

    python -m maipai_packages.coding_companion.hook working
    python -m maipai_packages.coding_companion.hook waiting --kind permission --project my-app
    python -m maipai_packages.coding_companion.hook finished --project my-app

The token is read from the token file (`stackchan coding-token` prints where it is), never from an argument or an
environment variable. The hook never fails the agent: when the robot cannot be reached it prints one line and exits 0.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def send(state: str, kind: str, project: str, port: int, token_file: Path) -> str:
    try:
        token = token_file.read_text(encoding="utf-8").strip()
    except OSError:
        return f"coding companion: no token file at {token_file}. Run `stackchan coding-token` first."
    body = {"state": state}
    if kind:
        body["kind"] = kind
    if project:
        body["project"] = project
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/status",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as reply:
            return "" if reply.status == 200 else f"coding companion: the host answered {reply.status}."
    except urllib.error.HTTPError as error:
        return f"coding companion: the host refused it ({error.code}). Check that the token file is the current one."
    except (urllib.error.URLError, OSError):
        return "coding companion: the host is not reachable. Is the coding companion switched on in robot.toml?"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="coding-companion-hook", description=__doc__.splitlines()[0])
    parser.add_argument("state", choices=("working", "waiting", "finished"))
    parser.add_argument("--kind", choices=("permission", "question", "finished", ""), default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--port", type=int, default=8052)
    parser.add_argument("--token-file", type=Path, default=None)
    args = parser.parse_args(argv)
    token_file = args.token_file
    if token_file is None:
        from maipai_packages.coding_companion.server import default_token_path

        token_file = default_token_path()
    message = send(args.state, args.kind, args.project, args.port, token_file)
    if message:
        print(message, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
