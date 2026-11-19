# Contributing

Thanks for looking at MaiPai for StackChan. This page is short. The full rules are in the [developer guide on contributing](docs/dev/contributing.md). Read that page before you change anything.

## What the rules say

- No dependency on any other MaiPai repo: no import, submodule or runtime call.
- An optional feature that is off costs no memory. Every firmware step passes the memory gate.
- Every feature has a body half and a brain half. A missing brain half hides the feature.
- Every error message says what went wrong and what to do.
- Follow the [writing style](docs/STYLE.md).
- Run `bash scripts/check.sh` before you finish. It must print "hygiene: ok".
- Contributions are under AGPL-3.0. Never commit keys, real addresses or names. Examples use 192.0.2.x and example.com.

## Pull requests

The developer guide does not describe a pull request process yet, so this page does not either. If you want to change code, open an issue first and say what you want to change.

## Report a bug

1. Run `stackchan check` and read [Troubleshooting](docs/user/troubleshooting.md).
2. If it still fails, open an issue with the bug report form.
3. Paste the `stackchan check` output. Never paste a token, a Wi-Fi password or the pairing code.

For a security problem, do not open a public issue with details. Follow [SECURITY.md](SECURITY.md).

## Propose a feature

Open an issue with the feature request form. Say what you want the robot to do and why. Read [What the robot can do](docs/user/features.md) first, in case it is already there or planned. [The scope notes](docs/STYLE.md) explain which features belong in the core and which need MaiPai Home.

## Conduct

Be kind. See the [code of conduct](CODE_OF_CONDUCT.md).
