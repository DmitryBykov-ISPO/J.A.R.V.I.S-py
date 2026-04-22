from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Union


class SchemaError(ValueError):
    pass


@dataclass
class ExeAction:
    file: str
    wait: Optional[bool] = None
    delay_ms: Optional[int] = None

    type: str = "exe"

    def to_dict(self) -> dict:
        out: dict = {"type": "exe", "file": self.file}
        if self.wait is not None:
            out["wait"] = bool(self.wait)
        if self.delay_ms is not None:
            out["delay_ms"] = int(self.delay_ms)
        return out


@dataclass
class PlaySoundAction:
    name: str
    type: str = "play_sound"

    def to_dict(self) -> dict:
        return {"type": "play_sound", "name": self.name}


@dataclass
class SystemAction:
    op: str
    type: str = "system"

    def to_dict(self) -> dict:
        return {"type": "system", "op": self.op}


@dataclass
class SleepAction:
    ms: int
    type: str = "sleep"

    def to_dict(self) -> dict:
        return {"type": "sleep", "ms": int(self.ms)}


@dataclass
class ShellAction:
    cmd: str
    wait: Optional[bool] = None
    type: str = "shell"

    def to_dict(self) -> dict:
        out: dict = {"type": "shell", "cmd": self.cmd}
        if self.wait is not None:
            out["wait"] = bool(self.wait)
        return out


@dataclass
class UrlAction:
    href: str
    type: str = "url"

    def to_dict(self) -> dict:
        return {"type": "url", "href": self.href}


@dataclass
class KeysAction:
    sequence: Optional[str] = None
    text: Optional[str] = None
    type: str = "keys"

    def to_dict(self) -> dict:
        out: dict = {"type": "keys"}
        if self.sequence is not None:
            out["sequence"] = self.sequence
        if self.text is not None:
            out["text"] = self.text
        return out


Action = Union[
    "ExeAction",
    "PlaySoundAction",
    "SystemAction",
    "SleepAction",
    "ShellAction",
    "UrlAction",
    "KeysAction",
    "MultiAction",
]


@dataclass
class MultiAction:
    steps: List[Action] = field(default_factory=list)
    type: str = "multi"

    def to_dict(self) -> dict:
        return {"type": "multi", "steps": [s.to_dict() for s in self.steps]}


VALID_SYSTEM_OPS = ("volume_mute", "volume_unmute", "exit")
VALID_SOUND_NAMES = (
    "ok", "ready", "thanks", "not_found", "greet", "run", "stupid", "off",
)


def action_from_dict(data: Any) -> Action:
    if not isinstance(data, dict):
        raise SchemaError("action must be a mapping")
    t = data.get("type")
    if not t:
        raise SchemaError("action is missing 'type'")

    if t == "exe":
        if not data.get("file"):
            raise SchemaError("exe action requires 'file'")
        return ExeAction(
            file=data["file"],
            wait=data.get("wait"),
            delay_ms=data.get("delay_ms"),
        )
    if t == "play_sound":
        name = data.get("name")
        if not name:
            raise SchemaError("play_sound action requires 'name'")
        if name not in VALID_SOUND_NAMES:
            raise SchemaError(f"unknown sound name: {name}")
        return PlaySoundAction(name=name)
    if t == "system":
        op = data.get("op")
        if op not in VALID_SYSTEM_OPS:
            raise SchemaError(f"unknown system op: {op}")
        return SystemAction(op=op)
    if t == "sleep":
        ms = data.get("ms")
        if not isinstance(ms, int) or ms < 0:
            raise SchemaError("sleep action requires non-negative integer 'ms'")
        return SleepAction(ms=ms)
    if t == "shell":
        cmd = data.get("cmd")
        if not cmd or not isinstance(cmd, str):
            raise SchemaError("shell action requires non-empty 'cmd' string")
        return ShellAction(cmd=cmd, wait=data.get("wait"))
    if t == "url":
        href = data.get("href")
        if not href or not isinstance(href, str):
            raise SchemaError("url action requires non-empty 'href' string")
        return UrlAction(href=href)
    if t == "keys":
        sequence = data.get("sequence")
        text = data.get("text")
        if not sequence and not text:
            raise SchemaError("keys action requires 'sequence' or 'text'")
        if sequence and text:
            raise SchemaError("keys action cannot have both 'sequence' and 'text'")
        return KeysAction(sequence=sequence, text=text)
    if t == "multi":
        steps_raw = data.get("steps")
        if not isinstance(steps_raw, list) or not steps_raw:
            raise SchemaError("multi action requires non-empty 'steps' list")
        steps = [action_from_dict(s) for s in steps_raw]
        return MultiAction(steps=steps)

    raise SchemaError(f"unknown action type: {t}")


@dataclass
class CommandEntry:
    cmd_id: str
    phrases: List[str]
    action: Action
    confirm_sound: Optional[str] = None

    def to_dict(self) -> dict:
        body: dict = {
            "phrases": list(self.phrases),
            "action": self.action.to_dict(),
        }
        if self.confirm_sound is not None:
            body["confirm_sound"] = self.confirm_sound
        return body


def command_from_dict(cmd_id: str, data: Any) -> CommandEntry:
    if not isinstance(data, dict):
        raise SchemaError(f"command {cmd_id!r} body must be a mapping")
    phrases = data.get("phrases")
    if not isinstance(phrases, list) or not phrases:
        raise SchemaError(f"command {cmd_id!r} requires non-empty 'phrases' list")
    if not all(isinstance(p, str) and p.strip() for p in phrases):
        raise SchemaError(f"command {cmd_id!r} phrases must be non-empty strings")
    action_raw = data.get("action")
    if action_raw is None:
        raise SchemaError(f"command {cmd_id!r} requires 'action'")
    action = action_from_dict(action_raw)
    confirm = data.get("confirm_sound")
    if confirm is not None and confirm not in VALID_SOUND_NAMES:
        raise SchemaError(f"command {cmd_id!r} has unknown confirm_sound: {confirm}")
    return CommandEntry(cmd_id=cmd_id, phrases=phrases, action=action, confirm_sound=confirm)


_SLUG_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slugify(phrase: str) -> str:
    lowered = phrase.lower().strip()
    out_chars: list = []
    for ch in lowered:
        if ch in _SLUG_TRANSLIT:
            out_chars.append(_SLUG_TRANSLIT[ch])
        elif ch.isalnum() and ord(ch) < 128:
            out_chars.append(ch)
        elif ch in (" ", "_", "-"):
            out_chars.append("_")
    slug = "".join(out_chars)
    while "__" in slug:
        slug = slug.replace("__", "_")
    slug = slug.strip("_")
    return slug or "cmd"
