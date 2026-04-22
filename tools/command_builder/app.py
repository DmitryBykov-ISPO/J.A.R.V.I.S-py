from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

import webview

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = Path(__file__).resolve().parent / "web"
COMMANDS_YAML = REPO_ROOT / "commands.yaml"
CUSTOM_COMMANDS_DIR = REPO_ROOT / "custom-commands"
SOUND_DIR = REPO_ROOT / "sound"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.command_builder.schema import (
    CommandEntry,
    SchemaError,
    VALID_SOUND_NAMES,
    action_from_dict,
    command_from_dict,
    slugify,
)
from tools.command_builder import yaml_writer


class Bridge:
    def list_existing_commands(self):
        try:
            return yaml_writer.list_command_ids(COMMANDS_YAML)
        except Exception as ex:
            return {"error": str(ex)}

    def list_exes(self):
        if not CUSTOM_COMMANDS_DIR.exists():
            return []
        names = []
        for p in sorted(CUSTOM_COMMANDS_DIR.iterdir()):
            if p.suffix.lower() == ".exe":
                names.append(p.stem)
        return names

    def list_sound_names(self):
        return list(VALID_SOUND_NAMES)

    def preview_sound(self, name):
        if name not in VALID_SOUND_NAMES:
            return {"ok": False, "error": "unknown sound"}
        candidates = []
        if name in ("ok", "greet"):
            for i in (1, 2, 3):
                candidates.append(SOUND_DIR / f"{name}{i}.wav")
        candidates.append(SOUND_DIR / f"{name}.wav")
        target = next((c for c in candidates if c.exists()), None)
        if target is None:
            return {"ok": False, "error": f"file not found for {name}"}

        def _play():
            try:
                import simpleaudio as sa
                wave_obj = sa.WaveObject.from_wave_file(str(target))
                play_obj = wave_obj.play()
                play_obj.wait_done()
            except Exception:
                pass

        threading.Thread(target=_play, daemon=True).start()
        return {"ok": True}

    def slugify(self, phrase):
        return slugify(phrase or "")

    def validate_draft(self, draft_json):
        try:
            data = json.loads(draft_json) if isinstance(draft_json, str) else draft_json
            cmd_id = data.get("cmd_id") or ""
            if not cmd_id.strip():
                return {"ok": False, "error": "Не указан идентификатор команды"}
            entry = command_from_dict(cmd_id, {
                "phrases": data.get("phrases") or [],
                "action": data.get("action") or {},
                **({"confirm_sound": data["confirm_sound"]} if data.get("confirm_sound") else {}),
            })
            return {"ok": True, "id": entry.cmd_id}
        except SchemaError as ex:
            return {"ok": False, "error": str(ex)}
        except Exception as ex:
            return {"ok": False, "error": f"Внутренняя ошибка: {ex}"}

    def save_command(self, draft_json):
        try:
            data = json.loads(draft_json) if isinstance(draft_json, str) else draft_json
            cmd_id = (data.get("cmd_id") or "").strip()
            if not cmd_id:
                return {"ok": False, "error": "Не указан идентификатор команды"}
            entry = command_from_dict(cmd_id, {
                "phrases": data.get("phrases") or [],
                "action": data.get("action") or {},
                **({"confirm_sound": data["confirm_sound"]} if data.get("confirm_sound") else {}),
            })
            existing = set(yaml_writer.list_command_ids(COMMANDS_YAML))
            if entry.cmd_id in existing and not data.get("overwrite"):
                return {"ok": False, "error": f"Команда {entry.cmd_id} уже существует"}
            if data.get("overwrite"):
                yaml_writer.upsert_command(entry, path=COMMANDS_YAML)
            else:
                yaml_writer.append_command(entry, path=COMMANDS_YAML)
            return {"ok": True, "id": entry.cmd_id}
        except SchemaError as ex:
            return {"ok": False, "error": str(ex)}
        except Exception as ex:
            return {"ok": False, "error": f"Не удалось сохранить: {ex}"}

    def llm_suggest(self, prompt):
        try:
            from tools.command_builder import llm_suggest as ls
            return ls.suggest(prompt or "")
        except Exception as ex:
            return {"ok": False, "error": f"LLM недоступен: {ex}"}


def main():
    bridge = Bridge()
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise SystemExit(f"web/index.html not found at {index_path}")
    webview.create_window(
        title="J.A.R.V.I.S — конструктор команд",
        url=str(index_path),
        js_api=bridge,
        width=900,
        height=720,
        min_size=(720, 560),
        background_color="#0a1214",
    )
    webview.start()


if __name__ == "__main__":
    main()
