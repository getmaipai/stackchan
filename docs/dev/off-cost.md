# Cost of a switched-off feature in the plain image

Image: `b43/build-plain`, 3727728 bytes. Static sizes (`size`): text 2752847, data 997580, bss 6364693.

A feature that is off must show 0 symbols, 0 bytes and 0 strings. Made by `scripts/off-cost.sh`; re-run it after any change to a switch.

| Feature (switch) | Symbols | Bytes | Strings | Result |
|---|---|---|---|---|
| Talking over the robot (CONFIG_MAIPAI_TALK_OVER, microphone slot tools) | 0 | 0 | 0 | zero cost |
| Echo canceller and barge-in (CONFIG_MAIPAI_TALK_OVER_AEC) | 0 | 0 | 0 | zero cost |
| Encrypted link and pairing (CONFIG_MAIPAI_LINK_PSK) | 0 | 0 | 0 | zero cost |
| Bench and serial tools (CONFIG_MAIPAI_SERIAL_TOOLS) | 0 | 0 | 0 | zero cost |
| Heap trace (CONFIG_HEAP_TRACING_STANDALONE) | 0 | 0 | 0 | zero cost |

Check that the script can see a cost: on the heap image (bench, talk-over, echo canceller and heap trace on) it reports 11 talk-over symbols (2,633 bytes), 8 echo canceller symbols (1,235 bytes), 52 bench symbols (571,628 bytes) and 8 heap trace symbols (961 bytes). The encrypted link row needs the `linkpsk` image to show a cost.
