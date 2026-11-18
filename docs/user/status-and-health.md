# See what is running

Two ways, the same answer in plain words.

## On the page

Open the settings page on the host computer and go to `/health` (for example `http://127.0.0.1:8777/health`). It shows:

- One sentence at the top: everything is running, something is restarting, or something needs you.
- Each part of the host, and whether it is running.
- Each robot, whether it is connected, when it was last seen, and its own parts.
- What to do, when something is wrong.

The page refreshes by itself.

## In a terminal

```bash
stackchan status
```

It prints the same information. If the host is not running, it says so and tells you to run `stackchan service start`.

## What the words mean

- **Running:** working.
- **Restarting:** the host noticed a part stopped or stopped answering and is starting it again. This is normal for a moment. Other parts and other robots are not affected.
- **Stopped after repeated failures:** a part failed five times in ten minutes, so the host stopped trying. The page says what went wrong and what to do. After you fix it, restart the host.

One robot having a problem never stops another robot.
