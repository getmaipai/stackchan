# Own-LLM brain

The own-LLM brain makes text turns against an owner-configured OpenAI-compatible chat-completions URL. It streams complete sentences to the configured speech callback as they arrive and retains a bounded message history in process memory. A conversation starts with the configured persona. Timers remain a unit capability; household, identity, vision, and reminder features are hidden.

Content safety is the responsibility of the connected language model and the owner's persona prompt. This brain adds no content filter.

## Configuration

In `robot.toml`, `[llm]` accepts:

- `url` and `model`: chat-completions base URL and model name.
- `api_key_env`: optional environment variable name holding the API key. The key itself is never stored in the file.
- `persona`: system prompt text.
- `timeout_seconds`: HTTP request timeout.
- `history_messages`: maximum prior messages retained for each conversation.
- `stt_url` and `tts_url`: OpenAI-compatible audio service base URLs. When unset, local speech engines are selected if model paths are configured.
- `stt_model_dir`, `tts_model`, `tts_tokens`, and `tts_data_dir`: local Moonshine and Piper model paths.

## Failure messages

A model connection failure says: “I could not reach the model at <host>; check robot.toml.” Missing local STT or TTS setup says to set the corresponding service URL or install/configure a speech model. Invalid or unsupported audio response data identifies the audio format problem.
