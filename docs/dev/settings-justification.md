# Settings justification (owner decision 20)

One row per `robot.toml` key: who needs it, what it costs, why the default is not enough, and the disposition from `host-choices-audit.md`. `scripts/choices-check.py` fails when a key has no row.

| Key | Who needs it | Cost | Why the default is not enough | Disposition |
|---|---|---|---|---|
| `brain` | anyone | one question | Home or your own stack is a real choice | keep |
| `units` | a home with several robots needing different models | a table to write | global settings cover most homes | advanced |
| `llm.url` | own-stack users | an address | no address can be guessed | keep |
| `llm.model` | own-stack users | a name | the server decides the names | keep |
| `llm.stt_url` | own-stack users | an address | no address can be guessed | keep |
| `llm.tts_url` | own-stack users | an address | no address can be guessed | keep |
| `llm.api_key_env` | a server that needs a key | a variable name | most local servers need none | advanced |
| `llm.persona` | people who want a different voice of the robot | some writing | a neutral persona is set | advanced |
| `llm.timeout_seconds` | slow models | a number | 30 s fits talking | advanced |
| `llm.history_messages` | long chats | a number | 20 fits memory and cost | advanced |
| `llm.stt_model_dir` | the local stack | a folder | written by the install | automatic |
| `llm.tts_model` | the local stack | a file | written by the install | automatic |
| `llm.tts_tokens` | none by hand | a file | found beside the model | automatic |
| `llm.tts_data_dir` | none by hand | a folder | found beside the model | automatic |
| `home.url` | Home users | an address | Home cannot be guessed | keep |
| `home.language` | anyone | a code | taken from the first choice | automatic |
| `home.quiet_hours_from` | a household | a time | the robot cannot know bedtime | keep |
| `home.quiet_hours_to` | a household | a time | the robot cannot know waking time | keep |
| `packages.memory_notes.enabled` | people who want notes | one switch | off costs nothing; notes are a choice | keep |
| `packages.memory_notes.people` | note keepers | names | names cannot be derived | keep |
| `packages.memory_notes.default_person` | a one-adult home | a name | a risk the owner chooses | keep |
| `packages.memory_notes.folder` | people who store notes elsewhere | a path | a private default folder exists | advanced |
| `packages.home_assistant.enabled` | Home Assistant users | one switch | off costs nothing | keep |
| `packages.home_assistant.url` | Home Assistant users | an address | cannot be guessed | keep |
| `packages.home_assistant.token_env` | Home Assistant users | a variable name | the token is never written in the file | keep |
| `packages.home_assistant.trigger` | people who dislike the phrase | a phrase | 'home assistant' works | advanced |
| `packages.home_assistant.cameras` | people with cameras | names | cannot be derived | keep |
| `packages.home_assistant.allow_plain_http` | a plain-http server | a safety relaxation | https is the default | advanced |
| `packages.home_assistant.allow_unidentified` | homes without voice recognition | a safety relaxation | refusing is the safe default | advanced |
| `packages.home_assistant.speakers` | homes with several people | names | cannot be derived | keep |
| `packages.coding_companion.enabled` | developers | one switch | off costs nothing | keep |
| `packages.coding_companion.show_request_text` | developers | a privacy choice | the safe default shows less | advanced |
| `packages.coding_companion.port` | a busy port | a number | the default port works | advanced |
| `packages.pantry.enabled` | people who want jokes, riddles and trivia the robot keeps | one switch | off costs nothing and imports nothing | keep |
| `packages.pantry.languages` | homes that use more than English | a list | one language is the right default | advanced |
| `packages.pantry.daily_cap` | people with a paid or slow model | a number | 200 calls a day is safe for most; a metered model needs a lower one | advanced |
| `packages.pantry.adult_humor` | adults who want a grown-up shelf | one switch | kids only is the safe default, and the owner must choose otherwise | keep |
| `packages.pantry.folder` | people who store it elsewhere | a path | a private default exists | advanced |
| `packages.wake_word_maker.enabled` | people who want a wake word | one switch | off costs nothing | keep |
| `packages.wake_word_maker.folder` | people who store it elsewhere | a path | a private default exists | advanced |
| `settings.lan` | people who use a phone | opens the page to the network | a risk the person must choose | keep |
| `remote.enabled` | people who want remote control | a risk | off is the safe default | keep |
| `update.source` | people who run their own releases | a path | the host's own release is the default | advanced |
| `update.trusted_key` | people who run their own releases | a key file | the owner's key is the default | advanced |
| `update.preset` | none | a choice | follows the installed image; to be removed with one image | advanced |
| `local_stack.enabled` | none by hand | internal | written by the Brain page | automatic |
| `local_stack.choice` | none by hand | internal | written by the Brain page | automatic |
