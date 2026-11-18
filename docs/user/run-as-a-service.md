# Keep the host running

The host should run all the time, even after a restart or a crash. One command sets that up. You run it once.

```bash
stackchan service install
```

What it does:

- **Mac:** starts the host when you log in, and starts it again if it stops.
- **Linux and Raspberry Pi:** starts the host when the computer starts and starts it again if it stops. If it says it needs one more step for starting before anyone logs in, it prints the exact line for an administrator.
- **Windows:** sets up a task that starts at login. This is written but not tested yet.

It runs the same program you would start by hand. Your settings, pairings and notes are not touched.

## Look after it

| Command | What it does |
|---|---|
| `stackchan service status` | Says if it is installed and running |
| `stackchan service start` | Starts it |
| `stackchan service stop` | Stops it until your next login |
| `stackchan service logs` | Shows the last lines of the log |
| `stackchan service uninstall` | Removes it. Your settings stay |

The log is kept in your data folder under `logs`. It never grows past about 25 MB: old files are replaced.

## If it keeps stopping

The host restarts itself, and a part that keeps failing is reported on the [status page](status-and-health.md) with what to do. If the whole program keeps stopping, run `stackchan service logs` and read the last lines.
