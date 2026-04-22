from dotenv import load_dotenv
import os

# Find .env file with os variables
load_dotenv("dev.env")

# Конфигурация
VA_NAME = 'Jarvis'
VA_VER = "0.1.0"
VA_ALIAS = ('джарвис',)
VA_TBR = ('скажи', 'покажи', 'ответь', 'произнеси', 'расскажи', 'сколько', 'слушай')

# Wake-words распознаются Vosk'ом с grammar-constraint. Добавляйте сюда
# варианты написания — Vosk с русской моделью может расшифровать "jarvis"
# как "джарвис", "жарвис" и т.п.
WAKE_WORDS = ('jarvis', 'джарвис')

# ID микрофона (можете просто менять ID пока при запуске не отобразится нужный)
# -1 это стандартное записывающее устройство
MICROPHONE_INDEX = -1

# Путь к браузеру Google Chrome
CHROME_PATH = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s'

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
