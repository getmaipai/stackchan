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
