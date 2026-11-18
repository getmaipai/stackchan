"""Small, dependency-light audio helpers for local wake-word experiments."""
import wave
import numpy as np

SAMPLE_RATE = 16000
CLIP_SECONDS = 1.0
N_FFT = 400
HOP = 160
N_MELS = 40


def read_wav(path):
    with wave.open(str(path), "rb") as f:
        if f.getnchannels() != 1 or f.getsampwidth() != 2:
            raise ValueError("WAV must be mono 16-bit PCM")
        rate = f.getframerate()
        data = np.frombuffer(f.readframes(f.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    return data, rate


def write_wav(path, audio, sample_rate=SAMPLE_RATE):
    audio = np.asarray(audio, dtype=np.float32)
    pcm = np.clip(audio, -1, 1)
    pcm = (pcm * 32767).astype("<i2")
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sample_rate); f.writeframes(pcm.tobytes())


def _mel_filter():
    def mel(hz): return 2595.0 * np.log10(1.0 + hz / 700.0)
    def hz(m): return 700.0 * (10 ** (m / 2595.0) - 1.0)
    points = hz(np.linspace(mel(0), mel(SAMPLE_RATE / 2), N_MELS + 2))
    bins = np.floor((N_FFT + 1) * points / SAMPLE_RATE).astype(int)
    bank = np.zeros((N_MELS, N_FFT // 2 + 1), dtype=np.float32)
    for m in range(1, N_MELS + 1):
        l, c, r = bins[m - 1:m + 2]
        for k in range(l, c):
            if 0 <= k < bank.shape[1] and c != l: bank[m - 1, k] = (k - l) / (c - l)
        for k in range(c, r):
            if 0 <= k < bank.shape[1] and r != c: bank[m - 1, k] = (r - k) / (r - c)
    return bank

_MEL = _mel_filter()


def features(audio):
    x = np.asarray(audio, dtype=np.float32).reshape(-1)
    need = SAMPLE_RATE
    if len(x) < need: x = np.pad(x, (0, need - len(x)))
    else: x = x[:need]
    frames = np.stack([x[i:i + N_FFT] for i in range(0, need - N_FFT + 1, HOP)])
    spec = np.abs(np.fft.rfft(frames * np.hanning(N_FFT).astype(np.float32), axis=1)) ** 2
    return np.log(np.maximum(spec @ _MEL.T, 1e-8)).astype(np.float32)


def fix_length(audio, rate=SAMPLE_RATE):
    x = np.asarray(audio, dtype=np.float32).reshape(-1)
    if rate != SAMPLE_RATE and len(x):
        n = max(1, int(round(len(x) * SAMPLE_RATE / rate)))
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    if len(x) < SAMPLE_RATE: return np.pad(x, (0, SAMPLE_RATE - len(x))).astype(np.float32)
    return x[:SAMPLE_RATE].astype(np.float32)
