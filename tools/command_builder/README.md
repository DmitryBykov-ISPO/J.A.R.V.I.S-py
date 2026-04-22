# Конструктор команд (developer notes)

GUI-надстройка для редактирования `commands.yaml` без ручной правки YAML. Запускается отдельным процессом, не зависит от рантайма Jarvis.

## Запуск

```
python -m tools.command_builder
```

или из корня репо `run_builder.bat`.

## Стек

- `pywebview` (бэкенд EdgeWebView2 на Windows) — оборачивает локальный HTML.
- Frontend — vanilla JS + CSS, без сборки. Vendored `js-yaml` только для предпросмотра YAML на стороне UI.
- `ruamel.yaml` — чтение/запись `commands.yaml` с сохранением комментариев и форматирования.
- `pyautogui` — рантайм для action-типа `keys`.

## Структура

```
tools/command_builder/
  __main__.py        точка входа python -m
  app.py             pywebview bootstrap + Python bridge (js_api)
  schema.py          dataclass-схема action-блоков и валидация
  yaml_writer.py     atomic write + .bak бэкап перед каждой записью
  llm_suggest.py     Groq/OpenAI SDK 1.x, response_format=json_object
  web/               frontend
  tests/             pytest для schema + writer
```

## Bridge API (методы класса `Bridge` в `app.py`)

Все методы возвращают сериализуемые структуры. Ошибки идут как `{"ok": false, "error": "..."}`.

| метод | назначение |
|-------|-----------|
| `list_existing_commands()` | список ключей верхнего уровня в `commands.yaml` |
| `list_exes()` | basename'ы `*.exe` из `custom-commands/` |
| `list_sound_names()` | разрешённые имена для `play_sound` (из `schema.VALID_SOUND_NAMES`) |
| `preview_sound(name)` | проигрывает звук в фоновом потоке через `simpleaudio` |
| `slugify(phrase)` | транслит для генерации `cmd_id` |
| `validate_draft(json_str)` | прогон через `command_from_dict` |
| `save_command(json_str)` | append/upsert + бэкап (`overwrite: true` чтобы перезаписать) |
| `llm_suggest(prompt)` | Groq → JSON → провалидированный action-блок |

## Расширение схемы (новый тип action)

1. В `schema.py`: добавить dataclass с полем `type` и методом `to_dict()`. Включить в Union `Action`. Расширить `action_from_dict()`.
2. В `tests/test_schema.py`: добавить roundtrip + negative-case тесты.
3. В `web/app.js`:
   - карточка в `#action-grid` (`index.html`);
   - ветка в `renderActionForm()`;
   - ветка в `updateAction()`;
   - ветка в `renderInlineEditor()` для использования внутри multi.steps.
4. В `main.py` → `run_action()`: обработчик нового `type`.
5. В `llm_suggest.py` → `_ACTION_SCHEMA_DOC`: описание для LLM.

## Бэкапы

`yaml_writer.append_command` / `upsert_command` перед записью копируют `commands.yaml` в `commands.yaml.bak` (через `shutil.copy2`). При запуске `app.py` вызывается `_check_yaml_health()` — если основной файл не парсится, в stderr печатается путь к `.bak` для ручного восстановления.

## Тесты

```
.venv\Scripts\python.exe -m pytest tools/command_builder/tests/
```
