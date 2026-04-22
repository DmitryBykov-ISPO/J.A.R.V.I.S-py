from __future__ import annotations

import io
import os
import shutil
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

from .schema import CommandEntry, SchemaError, command_from_dict


DEFAULT_YAML_PATH = Path("C:/Jarvis/python/commands.yaml")


def _make_yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)
    y.width = 4096
    return y


def load_yaml(path: Path = DEFAULT_YAML_PATH):
    y = _make_yaml()
    with open(path, "rt", encoding="utf-8") as f:
        return y.load(f) or {}


def list_command_ids(path: Path = DEFAULT_YAML_PATH) -> list:
    try:
        data = load_yaml(path)
    except FileNotFoundError:
        return []
    return list(data.keys())


def _dump_to_string(data) -> str:
    y = _make_yaml()
    buf = io.StringIO()
    y.dump(data, buf)
    return buf.getvalue()


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wt", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


def _backup(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    return bak


def append_command(entry: CommandEntry, path: Path = DEFAULT_YAML_PATH) -> None:
    try:
        data = load_yaml(path)
    except FileNotFoundError:
        data = {}
    if entry.cmd_id in data:
        raise SchemaError(f"command id already exists: {entry.cmd_id}")
    data[entry.cmd_id] = entry.to_dict()
    _backup(path)
    text = _dump_to_string(data)
    _atomic_write(path, text)


def upsert_command(entry: CommandEntry, path: Path = DEFAULT_YAML_PATH) -> None:
    try:
        data = load_yaml(path)
    except FileNotFoundError:
        data = {}
    data[entry.cmd_id] = entry.to_dict()
    _backup(path)
    text = _dump_to_string(data)
    _atomic_write(path, text)


def validate_file(path: Path = DEFAULT_YAML_PATH) -> list:
    data = load_yaml(path)
    out = []
    for cmd_id, body in data.items():
        plain_body = body
        out.append(command_from_dict(cmd_id, dict(plain_body)))
    return out
