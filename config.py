from dotenv import load_dotenv
import os

# Find .env file with os variables
load_dotenv("dev.env")

# Конфигурация
VA_NAME = 'Jarvis'
VA_VER = "0.2.0"
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
