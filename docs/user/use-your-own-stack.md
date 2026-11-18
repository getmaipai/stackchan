# Use your own stack

Use this when you already run a language model, a speech-to-text server and a text-to-speech server. Open the settings page on the host at `/brain` and fill in the second card.

1. **Language model address.** The address of an OpenAI-style server, without the `/v1` at the end. Press **Test**. It says if nothing answers, if the key was refused, or if the model name is not in the server's list.
2. **Model name.** The name your server uses.
3. **Speech to text address** and **Text to speech address.** Press **Test** on each. The test only checks that something answers there.
4. **Key variable (optional).** If your server needs a key, type the name of the variable that holds it. The key itself is never typed here.
5. Press **Use my own stack**, then restart the host.

If a test says "Nothing answered", check that the program is running, the address and the port. The host and the servers must be able to reach each other.

You can also set all of this in `robot.toml`. See [Settings](settings.md).
