# Web flasher

A static page. Put it in the same folder as a release made by `scripts/release.sh` (the folder holds `flash-manifest.json` and the images) and serve the folder over https (Web Serial needs a secure page; `localhost` also counts). Open `index.html` in Chrome or Edge.

- `flasher-core.js`: reads the manifest, downloads each file, checks each SHA-256, builds the write list. Tested under Node (`node --test flasher/test/core.test.mjs`, run by `host/tests/test_flasher_page.py`).
- `flasher.js`: the page; writes with esptool-js. It checks every file before it asks for the robot, and writes nothing if one file is wrong.
- `trusted-keys.json`: the release keys the page trusts. `scripts/release.sh` refuses a real release while the list is empty or lacks the signing key. The test-release box shows only on `localhost` or with `?test=1`, and then the page names the key id.
- `vendor/`: esptool-js 0.7.0 (Apache-2.0), copied unchanged.

Checked so far: the page loads a release, lists the files, and refuses a changed file before touching the robot (built-in browser). Not checked: a real write to a robot over USB (needs a person with a robot and a release key) and a fake serial port.
