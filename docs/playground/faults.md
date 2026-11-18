# Faults: when the host is away

A robot that works with a host (a computer that runs its brain) keeps working when the host goes away.

- After **45 seconds** without the host, the word Offline shows.
- After **10 minutes**, a notice says in plain words that it cannot reach Home and what to check. It shows again every 30 minutes.
- The robot keeps trying to reconnect, slowly at first, then less often the longer the host is away. When the host comes back it reconnects by itself.

You can see these in the playground: the Offline look and the notice are screens in the golden frames (`host-away-offline`, `host-away-notice-*`).

Back: [Start here](start-here.md).
