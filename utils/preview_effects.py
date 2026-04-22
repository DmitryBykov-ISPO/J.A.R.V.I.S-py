import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import effects
import tts


PHRASE = "Приветствую, сэр. Все системы в норме."
OUT_RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'sound', '_preview_silero_raw.wav')
OUT_FX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'sound', '_preview_silero_fx.wav')


def _render_raw(text: str) -> np.ndarray:
    audio = tts.model.apply_tts(text=text + "..",
                                speaker=tts.speaker,
                                sample_rate=tts.sample_rate,
                                put_accent=tts.put_accent,
                                put_yo=tts.put_yo)
    return np.asarray(audio, dtype=np.float32)


def _render_fx(raw: np.ndarray) -> np.ndarray:
    return effects.process(
        raw, tts.sample_rate,
        bandpass=(config.TTS_BANDPASS_LOW_HZ, config.TTS_BANDPASS_HIGH_HZ),
        reverb=(config.TTS_REVERB_WET, config.TTS_REVERB_DECAY_MS),
        pitch_semitones=config.TTS_PITCH_SEMITONES,
    )


def main():
    print(f"Synthesizing: {PHRASE!r}")
    raw = _render_raw(PHRASE)
    fx = _render_fx(raw)

    sf.write(OUT_RAW, raw, tts.sample_rate, subtype='PCM_16')
    sf.write(OUT_FX, fx, tts.sample_rate, subtype='PCM_16')

    dur_raw = len(raw) / tts.sample_rate
    dur_fx = len(fx) / tts.sample_rate
    print(f"raw: {OUT_RAW}  ({len(raw)} samples, {dur_raw:.2f}s)")
    print(f"fx : {OUT_FX}  ({len(fx)} samples, {dur_fx:.2f}s)")
    print("Open both in a media player and A/B compare.")


if __name__ == '__main__':
    main()
