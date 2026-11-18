"""Build an augmented, local train/validation dataset."""
import argparse, json, shlex, subprocess
from pathlib import Path
import numpy as np
from features import SAMPLE_RATE, features, fix_length, read_wav


def _wav_files(folder):
    return sorted(Path(folder).glob("*.wav")) if folder else []


def _noise(rng, kind, n):
    if kind == "silence": return np.zeros(n, np.float32)
    if kind == "white": return rng.normal(0, 1, n).astype(np.float32)
    if kind == "pink":
        w = rng.normal(0, 1, n); y = np.cumsum(w); y -= y.mean(); return (y / (y.std() + 1e-8)).astype(np.float32)
    t = np.arange(n) / SAMPLE_RATE
    return (np.sin(2 * np.pi * rng.uniform(50, 300) * t) + .25 * rng.normal(size=n)).astype(np.float32)


def _augment(x, rng):
    x = x.copy()
    if rng.random() < .7:
        shift = int(rng.integers(-2400, 2401)); x = np.roll(x, shift)
        if shift > 0: x[:shift] = 0
        elif shift < 0: x[shift:] = 0
    if rng.random() < .5:
        factor = rng.uniform(.85, 1.15); n = max(2, int(len(x) / factor))
        x = np.interp(np.linspace(0, len(x)-1, n), np.arange(len(x)), x)
        x = fix_length(x)
    if rng.random() < .6:
        noise = rng.normal(size=len(x)).astype(np.float32); snr = rng.uniform(5, 25)
        noise *= (np.sqrt(np.mean(x*x)) + 1e-6) / (np.sqrt(np.mean(noise*noise)) + 1e-6) / (10 ** (snr/20))
        x += noise
    if rng.random() < .5:
        alpha = rng.uniform(.75, .98); y = np.empty_like(x); y[0] = x[0]
        for i in range(1, len(x)): y[i] = x[i] - alpha * x[i-1]
        x = y
    x *= rng.uniform(.5, 1.5)
    return np.clip(x, -1, 1).astype(np.float32)


def build(positive_dir, output, negatives=None, tts_cmd=None, text="wake word", seed=0):
    rng = np.random.default_rng(seed)
    positives = []
    for p in _wav_files(positive_dir):
        a, rate = read_wav(p); positives.append(fix_length(a, rate))
    if tts_cmd:
        out = Path(output).parent / "tts-positive.wav"
        argv = [part.replace("{text}", text).replace("{out}", str(out)) for part in shlex.split(tts_cmd)]
        if not any("{out}" in p for p in shlex.split(tts_cmd)) or not any("{text}" in p for p in shlex.split(tts_cmd)):
            raise ValueError("--tts-cmd must include {text} and {out} placeholders")
        subprocess.run(argv, check=True)
        a, rate = read_wav(out); positives.append(fix_length(a, rate))
    if not positives: raise ValueError("No positive recordings found; add WAV files or use --tts-cmd")
    negatives_x = []
    for p in _wav_files(negatives):
        a, rate = read_wav(p); a = fix_length(a, rate); negatives_x.append(a)
    negatives_x += [_noise(rng, kind, SAMPLE_RATE) * .15 for kind in ("white", "pink", "hum", "silence") for _ in range(max(2, len(positives)))]
    raw_x = positives + negatives_x
    raw_y = [1] * len(positives) + [0] * len(negatives_x)
    xx=[]; yy=[]
    for a, y in zip(raw_x, raw_y):
        reps = 4 if y else 2
        for j in range(reps): xx.append(features(a if j == 0 else _augment(a, rng))); yy.append(y)
    order = rng.permutation(len(yy)); xx=np.asarray(xx, np.float32)[order]; yy=np.asarray(yy, np.int8)[order]
    val_n=max(2, int(round(len(yy)*.2))); val_idx=order[:0] # keep split after shuffle
    np.savez_compressed(output, x_train=xx[val_n:], y_train=yy[val_n:], x_val=xx[:val_n], y_val=yy[:val_n])
    Path(str(output)+".json").write_text(json.dumps({"seed":int(seed),"positive_recordings":len(positives),"negative_recordings":len(negatives_x),"train_count":len(yy)-val_n,"val_count":val_n}, indent=2)+"\n")
    return Path(output)

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--positives",required=True); p.add_argument("--negatives"); p.add_argument("--output",required=True); p.add_argument("--tts-cmd"); p.add_argument("--text",default="wake word"); p.add_argument("--seed",type=int,default=0)
    a=p.parse_args(); build(a.positives,a.output,a.negatives,a.tts_cmd,a.text,a.seed)
