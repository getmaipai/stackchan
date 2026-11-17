# Custom and alternate wake words (owner question, 2026-11-17)

Placement: unit firmware (the wake word must work with the host asleep and nothing leaving the robot). Local. Choosing the word is a setting; the models are data in the assets partition.

**What the unit has [from code]:** one wake word model, "Hi, Stack Chan", from the speech library's WakeNet family, loaded from the assets partition (patch 030). Stricter trigger mode 95 (L05), a self test (086), the echo-reference removal (L01), and a small stop word list (049). Only one wake word runs at a time.

**Options**
1. **Alternates from the speech library's own list.** Ship one to three more of the library's ready-made words in the assets partition and let the owner pick one on the settings page or the bot settings screen. Only the chosen model is loaded, so RAM stays the same; the cost is flash (a few hundred KB each [unverified; measure]). Changing the word restarts the audio front end (a few seconds, no reboot if the front end can be rebuilt; else one reboot). The list of ready-made words is the library's, not ours: which phrases exist must be checked against the current model package [unverified].
2. **A custom word made by the library's vendor.** Espressif trains a WakeNet model for a requested phrase. Terms, cost, turnaround and the license of the result are unverified; this is the right route for a final product name, because the model quality matches the stock word.
3. **A word the owner trains locally.** A small keyword model (a different engine, for example a tiny neural network trained on synthetic voices) runs beside the front end. It lets an owner pick any word, trained in hours on this Mac with no data sent anywhere. Costs: a second engine to integrate, a model of tens of KB plus a working buffer in PSRAM, more false accepts and misses than the stock word until tested, and a stricter gate. An experiment, not a promise.
4. **No word at all:** touch to talk (tap the face, or the Apps list) already exists, and the stop word stays armed only while the robot makes sound.

**Name and trademark:** "Hi, Stack Chan" uses the hardware maker's product name. A public release needs the owner's decision on the word (for example the product's own name) before any custom model is ordered; the trademark search already queued for the release covers it.

**Recommendation:** (a) keep the current word as the default; (b) check the library's list for one or two alternates and ship them if they pass the false-accept gate; (c) decide the final word with the owner and order a vendor model for it; (d) keep a local training experiment for later. Gate for any word: at least 90 percent accepts at 1 m and 2 m on clean clips, under one false accept per hour of background speech, music and TV (measured on the unit), no change in the memory gate, and it must work in each language the owner uses (one word may serve all languages).

**What to test first:** the false-accept rate of the current word in a meeting-like room (the owner's worry), because every alternate is compared with that number.
