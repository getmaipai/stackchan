# Coding companion and agent tools (package design, for review before building)

Status: design only, 2026-11-18. Placement: optional package `host/maipai_packages/coding_companion/`, off by default (decision 3 of 2026-11-18; open decision 9 defaults: request text on screen, no voice-to-task, project name only, not red).

## What it is
The robot shows what a coding agent running on the owner's computer is doing (working, waiting for you, finished) and says it aloud on request. It does not run code and does not hand the model a shell.

## What a model may trigger (the part to review)
- **Nothing by default.** Agent tools exist only as a fixed list in the package; the model sees a tool only when the owner lists it under `[packages.coding_companion] tools`.
- Each listed tool is read-only or presentation-only: `show_status(text)` (screen text, 60 characters, plain), `say_done()` (a fixed phrase), `ask_attention()` (the needs-you light and tone).
- No tool reads files, runs commands, opens addresses, sends messages or reaches the network. Tool arguments are length-limited and stripped of control characters; text is shown as plain text, never interpreted.
- Every call goes through the command bus, so mute, sleep, a child present and a remote cue still win. A model reply cannot widen the list.
- Input from the agent side arrives on a local socket that accepts only loopback and needs the settings-style token.

## Not in scope
Voice-to-task, reading the code aloud, anything red, project paths (only the project name).

## Review asked
The coordinator's reviewer, high effort, before any code: is the tool list safe, and can any text the agent sends reach the model prompt as an instruction?

## Review result and what was built (2026-11-18)

The Opus review was APPROVE WITH CHANGES; all ten items are folded in and built (`host/maipai_packages/coding_companion/`, `tests/test_coding_companion.py`, `tests/test_agent_source.py`). The "What a model may trigger" section above is replaced by this: **the model gets no tools from this package.**

1. Agent text never enters the model prompt, history or persona. Spoken status is a handler (`brain.handlers`) answering from a fixed phrase plus the cleaned project name, with no model call. Test: the model request body never holds status text.
2. No model tools in v1; no function calling. Presentation is driven only by the agent endpoint.
3. Its own token in its own 0600 file (`coding-companion-token`), not the settings token; only a Bearer header counts; loopback only; Host check; any `Origin` header refused; JSON only; 2 KB cap; lockout as for the settings token.
4. Brackets, hidden and control characters and non-ASCII are removed from every agent string; 60 characters.
5. Secret-looking text, paths and addresses are refused whole. The screen shows a fixed word by default; request text is opt-in (`show_request_text`).
6. The bus has a source `agent` (priority between routines and the model): only `light.look` and a quiet `sound.play`, no red, tone at most once a minute, light changes capped per minute, every gate applies. The source is set by the endpoint, never by the message.
7. There is no path back to the agent: no approvals, no commands. Any future approval needs its own review (touch only, never voice).
8. Logs hold the state word only; never the text.
9. The config is a strict model (`enabled`, `show_request_text`, `port`); an unknown key fails at load. Off means the package is not imported and the port is not opened.
10. Docs fixed: `features.md`, `core-extras-modules.md`, `docs/user/coding-companion.md` (no dictation, approvals, MCP or free-text speech).

The memory notes risk from the same review is fixed too: stored notes may not hold brackets or hidden characters, are fenced and marked as not instructions in the prompt, scrubbed again when read, and capped at 1,500 characters a turn.
