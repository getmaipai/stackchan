# Use the robot as a coding companion

The robot sits on your desk and shows what your coding agent is doing.

## Agent status

The face and the ring show the agent's state: thinking, working, waiting for you or done. Each state has its own shape and motion.
The robot can also speak a short update, or show it as a caption.

![The face with a working ring and a caption "Running tests".](../images/agent-status.svg)

## Build light

Add this to the end of a build script:

```
stackchan notify --status pass
```

Use `--status fail` when the build fails. The ring turns green on pass and red on fail, with a check or a cross, so it reads without colour.

![The ring green with a check, then red with a cross.](../images/build-light.svg)

## Dictation

Hold the button and speak. The host turns your words into text and sends them to the agent. Release the button to finish.

## Approvals

When the agent asks permission, the robot shows the request and waits. Touch the screen to approve or refuse.
Voice alone never approves. This is on purpose, so a stray sentence cannot allow an action.

## Let an agent drive the robot

The host offers an MCP endpoint. An agent can use it to show a face, speak or play a cue. It is off by default. Turn it on with
`mcp = true` and give the agent the token from `stackchan token`.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
