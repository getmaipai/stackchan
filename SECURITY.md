# Security

## Scan results

Results of the repository's own scan. They are produced by `python3 scripts/security-scan.py --write`, and each line says what it covered and what it did not. A step marked NOT RUN was not run; it is never a pass.

<!-- scan:begin -->
<!-- scan:end -->

What the scan does not do: it is not a penetration test, it does not read every line of the firmware, and the vendored web libraries in the flasher and the docs site have no package lock for a tool to audit.

## What the project promises

- Nothing in the robot or the host contacts a server you did not choose. The scan above runs the host for 30 seconds with an empty home and records every connection it opens.
- The settings page listens only on the computer it runs on until you turn on `lan = true`, and then asks every other device for a token. See [Keep the robot secure](docs/user/security.md).

## Report a problem privately

Please do not post a security problem in a public issue. Private reporting through GitHub's Security tab ("Report a vulnerability") is not switched on yet; until the owner turns it on, open a normal issue that says only "I have a security report" with no detail, and we will arrange a private way to receive it.

## Check it yourself

Point your own AI assistant at this repository with the prompt in [VERIFY.md](VERIFY.md).
