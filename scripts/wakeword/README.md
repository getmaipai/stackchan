# Local wake word experiment

This is a local starting point for training a wake word for the robot. It does not ship a model.

1. Make a folder for your recordings outside the repository. Record 20 one-second WAV clips of the word in your own voice. Use mono, 16-bit PCM at 16 kHz.
2. Choose another folder outside the repository for generated files. Record or collect negative WAV audio in a separate folder.
3. Build a dataset: `python scripts/wakeword/make_dataset.py --positives /path/positive --negatives /path/negative --output /path/data.npz --seed 3`.
4. Train: `python scripts/wakeword/train_kws.py /path/data.npz --output /path/model.npz`. Add `--export-c /path/model.h` to write a text header for a later firmware experiment.
5. Evaluate: `python scripts/wakeword/eval_kws.py /path/model.npz --negatives /path/long-negative --positives /path/held-out-positive --output /path/result.json`.
6. The accuracy is the share of clips classified correctly. Recall is the share of held-out wake-word clips accepted. False accepts per hour estimates how often long negative audio triggers the model. Higher thresholds usually mean fewer false accepts and more missed words.

Recordings, datasets and models stay in folders you choose. Nothing is uploaded. Keep them outside the repository so no model is committed. This is a starting point, not a certified model. Before any use, it must pass the false-accept gate in `docs/design/next-wake-word-2026-11-17.md` on the robot, including background speech, music and TV.
