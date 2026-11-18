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
