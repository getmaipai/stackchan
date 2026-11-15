# Switch the language

English and Spanish are included. One firmware works for both, and you pick the language at run time.

## Change the language

Set `language` in `robot.toml`, in the settings page on your host or on the robot. No reflash. No file edit is needed from the page.

## What changes

- Replies and speech: the host does this. Your speech models and your language model must handle Spanish. Test them before you rely on it.
- Screen text and captions: a language pack covers accents and the inverted marks.
- Numbers, dates and times are spoken in words, such as "las tres y media". Dates use day, month, year and a 24 hour clock.
- Error messages say what went wrong and what to do, in both languages. The Spanish docs come after the English ones.

## Limits

- The wake word is an English phrase today. A Spanish phrase needs a trained model. Until then the English phrase works as the robot's name.
- Spanish voice commands on the robot may not be ready. If not, say the wake word first, then the command. The host handles it.
- Chinese, Japanese and Korean text is an optional font pack. Right-to-left screens are not planned.

## Still need help?

Run `stackchan check`, then read [Troubleshooting](troubleshooting.md). If that does not fix it, open an issue on the Issues tab and tell us what you saw.
