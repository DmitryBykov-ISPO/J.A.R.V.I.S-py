import numpy as np
from scipy.signal import butter, sosfiltfilt


def _ensure_float32_mono(audio):
    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim > 1:
        arr = arr.mean(axis=1).astype(np.float32)
    return arr


def apply_bandpass(audio, sr, low_hz=200, high_hz=7000, order=4):
    arr = _ensure_float32_mono(audio)
    nyq = 0.5 * sr
    low = max(low_hz, 1) / nyq
    high = min(high_hz, int(nyq) - 1) / nyq
    if not (0 < low < high < 1):
        return arr
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, arr).astype(np.float32)


def apply_reverb(audio, sr, wet=0.20, decay_ms=100, taps=4):
    arr = _ensure_float32_mono(audio)
    if wet <= 0 or decay_ms <= 0:
        return arr
    dry = max(0.0, 1.0 - wet)
    out = dry * arr
    gap = max(1, int(sr * (decay_ms / 1000.0) / taps))
    gain = wet
    for i in range(1, taps + 1):
        delay = gap * i
        gain *= 0.6
        if delay >= len(arr):
            break
        padded = np.zeros_like(arr)
        padded[delay:] = arr[:len(arr) - delay]
        out += gain * padded
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    if peak > 0.99:
        out *= 0.99 / peak
    return out.astype(np.float32)


def apply_pitch(audio, sr, semitones=0):
    arr = _ensure_float32_mono(audio)
    if semitones == 0:
        return arr
    factor = 2.0 ** (semitones / 12.0)
    n_out = int(round(len(arr) / factor))
    if n_out <= 1:
        return arr
    src_idx = np.linspace(0, len(arr) - 1, num=n_out).astype(np.float32)
    lo = np.floor(src_idx).astype(np.int64)
    hi = np.clip(lo + 1, 0, len(arr) - 1)
    frac = (src_idx - lo).astype(np.float32)
    resampled = (1.0 - frac) * arr[lo] + frac * arr[hi]
    return resampled.astype(np.float32)


def process(audio, sr, bandpass=None, reverb=None, pitch_semitones=0):
    out = _ensure_float32_mono(audio)
    if bandpass is not None:
        low, high = bandpass
        out = apply_bandpass(out, sr, low, high)
    if reverb is not None:
        wet, decay_ms = reverb
        out = apply_reverb(out, sr, wet=wet, decay_ms=decay_ms)
    if pitch_semitones:
        out = apply_pitch(out, sr, semitones=pitch_semitones)
    return out
