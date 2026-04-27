from dotenv import load_dotenv
import os

# Find .env file with os variables
load_dotenv("dev.env")

# Конфигурация
VA_NAME = 'Jarvis'
VA_VER = "0.4.1"
VA_ALIAS = ('джарвис',)
VA_TBR = ('скажи', 'покажи', 'ответь', 'произнеси', 'расскажи', 'сколько', 'слушай')

# Wake-words распознаются Vosk'ом с grammar-constraint. Добавляйте сюда
# варианты написания — Vosk с русской моделью может расшифровать "jarvis"
# как "джарвис", "жарвис" и т.п.
WAKE_WORDS = ('jarvis', 'джарвис')

# ID микрофона (можете просто менять ID пока при запуске не отобразится нужный)
# -1 это стандартное записывающее устройство
MICROPHONE_INDEX = -1

BROWSER_PATHS = {
    'yandex':  'C:/Program Files/Yandex/YandexBrowser/Application/browser.exe',
    'chrome':  'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'firefox': 'C:/Program Files/Mozilla Firefox/firefox.exe',
    'edge':    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
}

# Токен Groq
GROQ_TOKEN = os.getenv('GROQ_TOKEN')
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

# VAD (webrtcvad) — определяет конец команды по тишине вместо фиксированных 10 сек.
# 0..3, выше — агрессивнее режет шум (но и обрезает речь).
VAD_AGGRESSIVENESS = 2
COMMAND_END_SILENCE_MS = 1200
COMMAND_MIN_SPEECH_MS = 500
COMMAND_MIN_LISTEN_MS = 1000
COMMAND_MAX_LISTEN_MS = 15000

TTS_EFFECTS_ENABLED = False
TTS_BANDPASS_LOW_HZ = 200
TTS_BANDPASS_HIGH_HZ = 7000
TTS_REVERB_WET = 0.20
TTS_REVERB_DECAY_MS = 100
TTS_PITCH_SEMITONES = 0

# Семантический матчинг команд через эмбеддинги MiniLM-L6-v2 (ONNX, CPU).
# Порог — косинусная близость [0..1]. На вход поступает уже отфильтрованная
# фраза (без алиасов и vа_tbr); 0.45 эмпирически отделяет валидные команды
# от шума, оставляя запас на разговорные перефразировки.
INTENT_SIMILARITY_THRESHOLD = 0.45

# Шумоподавление аудио перед Vosk на этапе захвата команды (после wake-word).
# Спектральное гейтирование через noisereduce; даёт небольшую латентность,
# поэтому выключено по умолчанию и применяется только к буферу команды.
DENOISE_ENABLED = False
DENOISE_PROP = 0.85
DENOISE_STATIONARY = False
