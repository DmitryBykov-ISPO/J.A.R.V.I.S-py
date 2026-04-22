# J.A.R.V.I.S (Python) — Bossiara13's fork

Голосовой ассистент для Windows с wake-word **«jarvis»**. Распознаёт речь локально через Vosk (русская модель), отвечает голосом через Silero TTS, а свободные вопросы (фразы, начинающиеся со слова «скажи …») отправляет в LLM на Groq и зачитывает ответ.

## Это форк

Форк репозитория [Priler/jarvis](https://github.com/Priler/jarvis) (автор оригинала — Abraham Tugalov, 2022). Лицензия наследуется: **CC BY-NC-SA 4.0** (см. [LICENSE.txt](LICENSE.txt)).

## Что отличается от оригинала

- Из истории удалены случайно закоммиченные секреты.
- Бэкенд LLM переключён с OpenAI на Groq (бесплатный тариф) через openai-совместимый API.
- Код обновлён под новую версию SDK `openai` (>=1.0); старый pre-1.0 интерфейс был сломан.
- Обновлена ветка/тэги (`dev`, `v0.0.1-import`), причёсан README и `requirements.txt`.

## Установка

Требуется **Python 3.11** (на 3.13 ряд зависимостей пока ставится с бубном).

```bash
git clone https://github.com/DmitryBykov-ISPO/J.A.R.V.I.S-py.git
cd J.A.R.V.I.S-py
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Скопируйте `dev.env` и заполните ключи:

- `PICOVOICE_TOKEN` — бесплатно на [console.picovoice.ai](https://console.picovoice.ai/).
- `GROQ_TOKEN` — бесплатно на [console.groq.com](https://console.groq.com/).

Vosk-модель для русского языка лежит в `model_small/` (уже в репозитории). Запуск:

```bash
python main.py
```

## Конфигурация

- `config.py`:
  - `MICROPHONE_INDEX = -1` — индекс микрофона (`-1` означает устройство по умолчанию). Если микрофонов несколько и берётся не тот, поменяйте число.
  - `GROQ_MODEL` — имя модели Groq (по умолчанию `llama-3.3-70b-versatile`).
- `commands.yaml` — набор голосовых команд и их вариантов для fuzzy-матчинга.
- `custom-commands/` — скомпилированные AHK-скрипты под конкретный сетап автора оригинала (переключение мониторов, управление Яндекс.Музыкой и т.п.). На вашей машине большая часть из них работать не будет, но ассистент запустится в любом случае.

## Использование

1. Скажите **«Джарвис»** (или **«jarvis»**) — ассистент даст звуковой сигнал готовности.
2. В течение 10 секунд произнесите команду:
   - либо одну из фраз из `commands.yaml` (открыть браузер, выключить звук и т.д.);
   - либо начните со слова **«скажи …»** — остаток фразы уйдёт в Groq, ответ будет зачитан вслух.

## Лицензия

CC BY-NC-SA 4.0 — см. [LICENSE.txt](LICENSE.txt). Авторство оригинала — Abraham Tugalov / Priler. Изменения в этом форке — Bossiara13 (Dmitry Bykov), 2026.
