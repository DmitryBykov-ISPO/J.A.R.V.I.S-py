from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import config
from tools.command_builder.schema import (
    SchemaError,
    VALID_SOUND_NAMES,
    VALID_SYSTEM_OPS,
    action_from_dict,
    slugify,
)


_ACTION_SCHEMA_DOC = """
Допустимые типы действий (action.type):

- exe — запуск .exe из custom-commands/
    {"type":"exe","file":"<basename.exe>","wait":<bool optional>,"delay_ms":<int optional>}
- play_sound — встроенный звук
    {"type":"play_sound","name":"<one of: %SOUNDS%>"}
- system — системная операция
    {"type":"system","op":"<one of: %SYS_OPS%>"}
- sleep — пауза в миллисекундах (только внутри multi)
    {"type":"sleep","ms":<int>}
- shell — PowerShell/cmd строка
    {"type":"shell","cmd":"<string>","wait":<bool optional>}
- url — открыть URL в системном браузере
    {"type":"url","href":"<https://...>"}
- keys — нажатие клавиш ИЛИ ввод текста (только одно из двух)
    {"type":"keys","sequence":"ctrl+shift+m"}
    {"type":"keys","text":"печатаемая строка"}
- multi — последовательность шагов
    {"type":"multi","steps":[<action>, ...]}
""".strip()


def _build_system_prompt(exe_names: list[str]) -> str:
    schema = (
        _ACTION_SCHEMA_DOC
        .replace("%SOUNDS%", ", ".join(VALID_SOUND_NAMES))
        .replace("%SYS_OPS%", ", ".join(VALID_SYSTEM_OPS))
    )
    if exe_names:
        exe_lines = "\n".join(f"  - {n}.exe" for n in exe_names)
    else:
        exe_lines = "  (папка custom-commands/ пуста)"
    return (
        "Ты помогаешь собрать команду для голосового ассистента Jarvis. "
        "Пользователь описывает желаемое поведение по-русски. "
        "Верни ОДИН JSON-объект ровно с такими полями:\n"
        "{\n"
        '  "cmd_id": "<латиница, snake_case, опционально — иначе будет сгенерирован>",\n'
        '  "phrases": ["<голосовая фраза 1>", "..."],\n'
        '  "action": <один action из схемы ниже>,\n'
        '  "confirm_sound": "<опционально, имя звука для подтверждения>"\n'
        "}\n\n"
        f"{schema}\n\n"
        "Доступные .exe файлы (используй ровно эти имена в action.file):\n"
        f"{exe_lines}\n\n"
        "Правила:\n"
        "- Только валидный JSON, без пояснений и markdown.\n"
        "- phrases — 1-3 коротких русских фразы, без слова-активатора «джарвис».\n"
        "- Если нужно несколько шагов — используй multi.\n"
        "- sleep валиден только внутри multi.steps."
    )


def _get_client():
    from openai import OpenAI
    if not config.GROQ_TOKEN:
        raise RuntimeError("GROQ_TOKEN не задан в dev.env")
    return OpenAI(api_key=config.GROQ_TOKEN, base_url=config.GROQ_BASE_URL)


def _list_exes() -> list[str]:
    custom = REPO_ROOT / "custom-commands"
    if not custom.exists():
        return []
    return sorted(p.stem for p in custom.iterdir() if p.suffix.lower() == ".exe")


def suggest(prompt: str) -> dict:
    user_prompt = (prompt or "").strip()
    if not user_prompt:
        return {"ok": False, "error": "Пустой запрос"}

    try:
        client = _get_client()
    except Exception as ex:
        return {"ok": False, "error": str(ex)}

    system_prompt = _build_system_prompt(_list_exes())

    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=800,
        )
    except Exception as ex:
        return {"ok": False, "error": f"Ошибка запроса к Groq: {ex}"}

    raw = response.choices[0].message.content or ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as ex:
        return {"ok": False, "error": f"Модель вернула не-JSON: {ex}", "raw": raw}

    phrases = parsed.get("phrases")
    if not isinstance(phrases, list) or not phrases:
        return {"ok": False, "error": "В ответе нет phrases", "raw": parsed}
    phrases = [p for p in phrases if isinstance(p, str) and p.strip()]
    if not phrases:
        return {"ok": False, "error": "phrases пуст после фильтрации", "raw": parsed}

    action_raw = parsed.get("action")
    if not isinstance(action_raw, dict):
        return {"ok": False, "error": "В ответе нет action", "raw": parsed}

    try:
        action_obj = action_from_dict(action_raw)
    except SchemaError as ex:
        return {"ok": False, "error": f"Action не прошёл валидацию: {ex}", "raw": parsed}

    cmd_id = parsed.get("cmd_id")
    if not isinstance(cmd_id, str) or not cmd_id.strip():
        cmd_id = slugify(phrases[0])

    confirm = parsed.get("confirm_sound")
    if confirm is not None and confirm not in VALID_SOUND_NAMES:
        confirm = None

    suggestion = {
        "cmd_id": cmd_id,
        "phrases": phrases,
        "action": action_obj.to_dict(),
    }
    if confirm:
        suggestion["confirm_sound"] = confirm

    return {"ok": True, "suggestion": suggestion}
