import time

import numpy as np
import sounddevice as sd
import torch

import config
import effects

language = 'ru'
model_id = 'ru_v3'
sample_rate = 48000  # 48000
speaker = 'aidar'  # aidar, baya, kseniya, xenia, random
put_accent = True
put_yo = True
device = torch.device('cpu')  # cpu или gpu
text = "Хауди Хо, друзья!!!"

model, _ = torch.hub.load(repo_or_dir='snakers4/silero-models',
                          model='silero_tts',
                          language=language,
                          speaker=model_id)
model.to(device)


def _post_process(audio):
    if not getattr(config, 'TTS_EFFECTS_ENABLED', False):
        return audio

    arr = np.asarray(audio, dtype=np.float32)
    low = getattr(config, 'TTS_BANDPASS_LOW_HZ', 0)
    high = getattr(config, 'TTS_BANDPASS_HIGH_HZ', 0)
    bandpass = (low, high) if low and high and high > low else None

    wet = float(getattr(config, 'TTS_REVERB_WET', 0.0))
    decay = int(getattr(config, 'TTS_REVERB_DECAY_MS', 0))
    reverb = (wet, decay) if wet > 0 and decay > 0 else None

    pitch = int(getattr(config, 'TTS_PITCH_SEMITONES', 0))

    return effects.process(arr, sample_rate,
                           bandpass=bandpass,
                           reverb=reverb,
                           pitch_semitones=pitch)


def synthesize(what: str):
    audio = model.apply_tts(text=what + "..",
                            speaker=speaker,
                            sample_rate=sample_rate,
                            put_accent=put_accent,
                            put_yo=put_yo)
    return _post_process(audio)


def va_speak(what: str):
    audio = synthesize(what)

    sd.play(audio, sample_rate * 1.05)
    time.sleep((len(audio) / sample_rate) + 0.5)
    sd.stop()
