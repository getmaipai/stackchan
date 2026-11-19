# Switch the language

English, Spanish, French, German, Portuguese and Italian are included. One firmware works for all of them, and you pick the language at run time. The settings page comes in all six. The translations have not been reviewed by native speakers, so tell us what reads wrong.

## Change the language

Pick the language on the settings page on your host, or on the robot. No reflash, and no file edit. If you use MaiPai Home, `language` under `[home]` in `robot.toml` sets the hub's language.

## What changes

- Replies and speech: the host does this. Your speech models and your language model must handle Spanish. Test them before you rely on it.
- Screen words (the date on the clock face, the names on timer chips): English is built into the robot. The other five are small language packs, a few hundred bytes each, that your computer sends to the robot when you pick the language. The robot keeps the pack, so it still shows the words after a restart with your computer off, and it shows English if the pack is ever missing or damaged. The Packs page of the settings shows which pack the robot holds.
- The robot's screen font draws plain letters only, so accents are dropped on the screen (août reads "aou"). Speech keeps every accent.
- Offline phrases (what the robot says when it cannot reach your computer): the Packs page can make them with your own voice, in English and Spanish, and send them to the robot. Without them it says the sentences built into its software.
- Numbers, dates and times are spoken in words, such as "las tres y media". Dates use day, month, year and a 24 hour clock.
- Error messages say what went wrong and what to do, in English and Spanish. These docs are in English only.

## Limits

- The wake word is an English phrase today. A Spanish phrase needs a trained model. Until then the English phrase works as the robot's name.
- Spanish voice commands on the robot may not be ready. If not, say the wake word first, then the command. The host handles it.
- Chinese, Japanese and Korean text is an optional font pack. Right-to-left screens are not supported.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
