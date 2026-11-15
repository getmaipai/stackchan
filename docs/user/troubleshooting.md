# Troubleshooting


Start with `stackchan check`. It tests each address you set and says what is wrong.

| What you see | What went wrong | What to do |
|---|---|---|
| Time shows `--:--` | The robot has no time yet. The host sends it. | Check the robot is paired and on the same Wi-Fi as the host. |
| Pairing code rejected | The code was wrong or the two minute window ended. Five wrong codes close it. | Run `stackchan pair` again and type the new code. |
| The robot cannot find the host | Discovery on your network failed. | Type the host address on the robot's Wi-Fi page. |
| The robot cannot join Wi-Fi | The password or network name is wrong. | Use the setup page the robot opens, or enter Wi-Fi again in the flasher. |
| The robot does not answer | The language model address is unreachable. | Check `llm_url` with `stackchan check`. Make sure the model is running. |
| The robot does not talk | The speech address is unreachable or blank without a built-in engine. | Check `tts_url`, or clear it to use the built-in voice. |
| A feature is missing | It needs something not set up, so it hides. | Open the web settings page. It names what is missing. |
| Saying "unmute" does nothing | Mute powers the microphone down, so the robot cannot hear you. | Tap the mouth, or use the web app. See [Mute, camera off and full quiet](mute-and-camera-off.md). |
| The robot says the versions do not match | The robot and the host use different contract versions. | Update the side the message names first. |
| An update failed | The robot did not pass its health check in 60 seconds. | It rolled back by itself. Read the release notes, then try again. |
| The robot will not start after a flash | The flash did not finish. | Use the USB recovery steps in `docs/dev/build-from-source.md`. |
| A language pack does not fit | The robot lacks space. | Remove a pack the page names, then install again. |
| The light bars pulse amber and the screen says "Offline" | The robot lost its link to your host or hub. | Check the host is on and on the same Wi-Fi or Tailscale. See [Take the robot on the go](use-it-anywhere.md). |
| The light bars stay green | Your voice is still being sent, so a turn is open. | Say "stop" or tap the screen to end the turn. |
| The light bars pulse cyan | The robot needs you: Wi-Fi setup, pairing, or a timer is ringing. | Follow the screen, or touch the robot to end a timer. See [Lights and sounds](lights-and-sounds.md). |
| The first word takes a long time | The model is too big for the computer, or it was not loaded yet. | See [Pick hardware and a model](hardware-and-models.md). |
| It will not dance to my music | Dance to music is off, the music is quiet, or the robot is muted. | Turn on Dance to music in the web settings, play clearer music nearby, and check mute. |
| "What is this" does nothing | That feature needs MaiPai Home. | Set `brain = "home"`. See [Compare](compare.md). |
| The robot says it cannot reach the host | Tailscale is off, or the key expired. | Paste a new key on the Network page. |
| The camera will not turn on | The camera is off in settings, or you tapped the eyes. | Set `camera = true`, then tap an eye to turn it back on. |
