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
| `stackchan service update` | Installs the new version beside the old one, switches to it and checks it is healthy. If it is not healthy within a minute, it goes back to the old version by itself |

The log is kept in your data folder under `logs`. It never grows past about 25 MB: old files are replaced.

## Update with a safety net

`stackchan service update` never replaces the running host in place. It installs the new version in its own folder, stops the service, switches, starts, and waits up to 60 seconds for the status page to say everything runs. If it does not, the old version is started again and `stackchan service status` says the update did not take. The last two versions are kept.

## If it keeps stopping

The host restarts itself, and a part that keeps failing is reported on the [status page](status-and-health.md) with what to do. If the whole program keeps stopping, run `stackchan service logs` and read the last lines.
