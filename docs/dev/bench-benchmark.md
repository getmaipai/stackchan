# Running a voice benchmark

The benchmark uses the fixed twenty prompt script in `host/bench/script-20.json`: ten short questions, five medium questions, then five turns that should be interrupted. Keep the room, Wi-Fi access point, robot position, microphone position and host settings the same between images.

## Run the comparison

1. Set aside about an hour. Prepare a microphone beside the robot and a recorder configured for 48 kHz mono or stereo WAV.
2. Flash the factory image. Start recording before the first question and note each question end time in seconds from the recording start. For interrupt prompts, say “stop” or touch the robot after the script's `interrupt_after_s` mark.
3. Run `stackchan bench-run --sim` once to check the tool and output path. A physical run needs the host voice service attached to the unit; it records host timestamps from that live link. The CLI simulator is for exercising the workflow and does not measure a physical voice path.
4. Run the same twenty prompts on each firmware image. Repeat in reverse order once to catch room or network drift. Label each run with the image name and keep all recordings.
5. Analyze each recording with `stackchan bench-analyze recording.wav --question-end SECONDS`. The analyzer reports reply activity segments and internal gaps over 80 ms. It uses energy thresholding, so listen to each flagged gap before treating it as a stutter.
6. Analyze a phone capture timestamp file with `stackchan bench-frames frametimes.txt`. Record 120 fps phone capture during a reply. The command reports interval median, p95 and estimated dropped frames.
7. Compare the JSON run files with `stackchan bench-compare first.json second.json`. The verdict applies the pass line in the benchmark plan. Keep the Markdown table and all-turn appendix with the recordings.

## What the numbers mean

Host timestamps use `time.monotonic`. Time to first audio and stop delay measured at the host link are estimates: they end at frame send or stop handling, not when the robot speaker becomes silent. Wake cue delay, acoustic first sound, stutters and longest acoustic gap need the recording and a screen capture where a wake cue is involved. Face smoothness comes from the phone frame timestamps. The benchmark does not open the camera.

For a manually marked question, record question end against the WAV start and pass that offset to `--question-end`. When a prompt is played through a host speaker, record the question's end in the same way. Use one output device and volume for both runs.

The owner supplies a spare hour, records beside the robot, flashes each image, and notes the host computer, robot hardware, language model and speech model names. Keep these labels with the JSON results so a later run can be compared fairly.
