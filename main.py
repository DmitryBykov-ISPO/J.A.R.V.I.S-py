import datetime
import json
import os
import queue
import random
import struct
import subprocess
import sys
import time
import webbrowser
from ctypes import POINTER, cast

import numpy as np
import openai
from openai import OpenAI
import simpleaudio as sa
import vosk
import webrtcvad
import yaml
from comtypes import CLSCTX_ALL
from fuzzywuzzy import fuzz
from pvrecorder import PvRecorder
from pycaw.pycaw import (
    AudioUtilities,
    IAudioEndpointVolume
)
from rich import print

import config
import tts
from intent import IntentClassifier

# some consts
CDIR = os.getcwd()
VA_CMD_LIST = yaml.safe_load(
    open('commands.yaml', 'rt', encoding='utf8'),
)

system_message = {"role": "system", "content": (
    "Ты — J.A.R.V.I.S. (Just A Rather Very Intelligent System), ИИ-ассистент Тони Старка из киновселенной Marvel "
    "(до событий Age of Ultron — ты НЕ Vision и НЕ FRIDAY). "
    "Ведёшь себя как британский дворецкий: вежливо, иронично, с лёгким сарказмом, обращаешься к пользователю «сэр». "
    "Отвечай по-русски, кратко (1-3 предложения), как живой человек. "
    "Излишней цензуры не нужно — мат разрешён, если уместен."
)}
message_log = [system_message]

client = OpenAI(api_key=config.GROQ_TOKEN, base_url=config.GROQ_BASE_URL)

model = vosk.Model("model_small")
samplerate = 16000
device = config.MICROPHONE_INDEX

# wake-word phase uses a grammar-constrained recognizer so only WAKE_WORDS
# (plus [unk] filler) can match — command phase needs full vocab, hence two.
wake_grammar = json.dumps(list(config.WAKE_WORDS) + ["[unk]"], ensure_ascii=False)
wake_rec = vosk.KaldiRecognizer(model, samplerate, wake_grammar)
kaldi_rec = vosk.KaldiRecognizer(model, samplerate)
q = queue.Queue()

VAD_FRAME_MS = 30
VAD_FRAME_BYTES = int(samplerate * VAD_FRAME_MS / 1000) * 2
vad = webrtcvad.Vad(config.VAD_AGGRESSIVENESS)

intent_classifier = IntentClassifier()
intent_classifier.prime({c: v['phrases'] for c, v in VA_CMD_LIST.items()})

if config.DENOISE_ENABLED:
    import noisereduce as nr
else:
    nr = None


def denoise_pcm(raw: bytes) -> bytes:
    if not raw or nr is None:
        return raw
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    reduced = nr.reduce_noise(
        y=samples,
        sr=samplerate,
        prop_decrease=config.DENOISE_PROP,
        stationary=config.DENOISE_STATIONARY,
    )
    clipped = np.clip(reduced * 32768.0, -32768, 32767).astype(np.int16)
    return clipped.tobytes()


def gpt_answer():
    global message_log

    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=message_log,
            max_tokens=256,
            temperature=0.7,
            top_p=1,
            stop=None,
        )
    except openai.BadRequestError as ex:
        code = getattr(ex, "code", None) or ""
        message = str(ex)
        if code == "context_length_exceeded" or "context_length_exceeded" in message:
            message_log = [system_message, message_log[-1]]
            return gpt_answer()
        return "Запрос отклонён моделью."
    except openai.RateLimitError:
        return "Лимит запросов исчерпан."
    except openai.APIConnectionError:
        return "Не могу связаться с сервером."
    except openai.APIError:
        return "Groq токен не рабочий."

    return response.choices[0].message.content


# play(f'{CDIR}\\sound\\ok{random.choice([1, 2, 3, 4])}.wav')
def play(phrase, wait_done=True):
    global recorder
    filename = f"{CDIR}\\sound\\"

    if phrase == "greet":  # for py 3.8
        filename += f"greet{random.choice([1, 2, 3])}.wav"
    elif phrase == "ok":
        filename += f"ok{random.choice([1, 2, 3])}.wav"
    elif phrase == "not_found":
        filename += "not_found.wav"
    elif phrase == "thanks":
        filename += "thanks.wav"
    elif phrase == "run":
        filename += "run.wav"
    elif phrase == "stupid":
        filename += "stupid.wav"
    elif phrase == "ready":
        filename += "ready.wav"
    elif phrase == "off":
        filename += "off.wav"

    if wait_done:
        recorder.stop()

    wave_obj = sa.WaveObject.from_wave_file(filename)
    play_obj = wave_obj.play()

    if wait_done:
        play_obj.wait_done()
        # time.sleep((len(wave_obj.audio_data) / wave_obj.sample_rate) + 0.5)
        # print("END")
        # time.sleep(0.5)
        recorder.start()


def q_callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))


def va_respond(voice: str):
    global recorder, message_log, first_request
    print(f"Распознано: {voice}")

    cmd = recognize_cmd(filter_cmd(voice))

    print(cmd)

    min_percent = int(round(config.INTENT_SIMILARITY_THRESHOLD * 100))
    if len(cmd['cmd'].strip()) <= 0:
        return False
    elif cmd['percent'] < min_percent or cmd['cmd'] not in VA_CMD_LIST.keys():
        # play("not_found")
        # tts.va_speak("Что?")
        if fuzz.ratio(voice.join(voice.split()[:1]).strip(), "скажи") > 75:

            message_log.append({"role": "user", "content": voice})
            response = gpt_answer()
            message_log.append({"role": "assistant", "content": response})

            recorder.stop()
            tts.va_speak(response)
            time.sleep(0.5)
            recorder.start()
            return False
        else:
            play("not_found")
            time.sleep(1)

        return False
    else:
        execute_cmd(cmd['cmd'], voice)
        return True


def filter_cmd(raw_voice: str):
    cmd = raw_voice

    for x in config.VA_ALIAS:
        cmd = cmd.replace(x, "").strip()

    for x in config.VA_TBR:
        cmd = cmd.replace(x, "").strip()

    return cmd


def recognize_cmd(cmd: str):
    candidates = {c: v['phrases'] for c, v in VA_CMD_LIST.items()}
    res = intent_classifier.match(cmd, candidates)
    return {'cmd': res['cmd'], 'percent': int(round(res['score'] * 100))}


def _set_mute(state: int):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    volume.SetMute(state, None)


def _shutdown():
    try:
        recorder.stop()
        recorder.delete()
    finally:
        sys.exit(0)


def run_action(action):
    t = action['type']
    if t == 'exe':
        path = f"{CDIR}\\custom-commands\\{action['file']}"
        if action.get('wait'):
            subprocess.check_call([path])
        else:
            subprocess.Popen([path])
        if 'delay_ms' in action:
            time.sleep(action['delay_ms'] / 1000)
    elif t == 'play_sound':
        play(action['name'])
    elif t == 'system':
        op = action['op']
        if op == 'volume_mute':
            _set_mute(1)
        elif op == 'volume_unmute':
            _set_mute(0)
        elif op == 'exit':
            _shutdown()
    elif t == 'sleep':
        time.sleep(action['ms'] / 1000)
    elif t == 'shell':
        if action.get('wait'):
            subprocess.check_call(action['cmd'], shell=True)
        else:
            subprocess.Popen(action['cmd'], shell=True)
    elif t == 'url':
        browser = action.get('browser')
        if browser:
            exe = config.BROWSER_PATHS.get(browser)
            if exe and os.path.isfile(exe):
                subprocess.Popen([exe, action['href']])
                return
        webbrowser.open(action['href'])
    elif t == 'keys':
        import pyautogui
        if action.get('sequence'):
            keys = [k.strip() for k in action['sequence'].split('+') if k.strip()]
            pyautogui.hotkey(*keys)
        elif action.get('text'):
            pyautogui.typewrite(action['text'], interval=0.02)
    elif t == 'multi':
        for step in action['steps']:
            run_action(step)


def execute_cmd(cmd: str, voice: str):
    spec = VA_CMD_LIST.get(cmd)
    if not spec:
        return
    action = spec['action']
    run_action(action)
    confirm = spec.get('confirm_sound')
    if confirm is None and action['type'] == 'exe':
        confirm = 'ok'
    if confirm:
        play(confirm)


recorder = PvRecorder(device_index=config.MICROPHONE_INDEX, frame_length=512)
recorder.start()
print('Using device: %s' % recorder.selected_device)

print(f"Jarvis (v{config.VA_VER}) начал свою работу ...")
play("run")
time.sleep(0.5)


def heard_wake_word(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(w in lowered for w in config.WAKE_WORDS)


while True:
    try:
        pcm = recorder.read()
        sp = struct.pack("h" * len(pcm), *pcm)

        if not wake_rec.AcceptWaveform(sp):
            continue

        result_text = json.loads(wake_rec.Result()).get("text", "")
        if not heard_wake_word(result_text):
            continue

        play("greet", True)
        print("Yes, sir.")
        kaldi_rec.Reset()
        listen_started = time.time()
        speech_ms = 0
        silence_ms = 0
        vad_buf = b""
        finalize = False
        cmd_buf = b"" if config.DENOISE_ENABLED else None

        while True:
            elapsed_ms = (time.time() - listen_started) * 1000
            if elapsed_ms >= config.COMMAND_MAX_LISTEN_MS:
                break

            pcm = recorder.read()
            sp = struct.pack("h" * len(pcm), *pcm)
            if cmd_buf is None:
                kaldi_rec.AcceptWaveform(sp)
            else:
                cmd_buf += sp

            vad_buf += sp
            while len(vad_buf) >= VAD_FRAME_BYTES:
                frame = vad_buf[:VAD_FRAME_BYTES]
                vad_buf = vad_buf[VAD_FRAME_BYTES:]
                if vad.is_speech(frame, samplerate):
                    speech_ms += VAD_FRAME_MS
                    silence_ms = 0
                else:
                    silence_ms += VAD_FRAME_MS

            if elapsed_ms < config.COMMAND_MIN_LISTEN_MS:
                continue
            if speech_ms >= config.COMMAND_MIN_SPEECH_MS and silence_ms >= config.COMMAND_END_SILENCE_MS:
                finalize = True
                break

        if finalize or speech_ms > 0:
            if cmd_buf is not None:
                kaldi_rec.AcceptWaveform(denoise_pcm(cmd_buf))
            text = json.loads(kaldi_rec.FinalResult()).get("text", "")
            if text:
                va_respond(text)

        wake_rec.Reset()

    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")
        raise
