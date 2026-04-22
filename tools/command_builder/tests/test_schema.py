from __future__ import annotations

import io
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from tools.command_builder.schema import (
    CommandEntry,
    ExeAction,
    KeysAction,
    MultiAction,
    PlaySoundAction,
    SchemaError,
    ShellAction,
    SleepAction,
    SystemAction,
    UrlAction,
    action_from_dict,
    command_from_dict,
    slugify,
)
from tools.command_builder.yaml_writer import (
    append_command,
    load_yaml,
    upsert_command,
)


def _roundtrip(action_obj):
    d = action_obj.to_dict()
    y = YAML()
    buf = io.StringIO()
    y.dump(d, buf)
    buf.seek(0)
    loaded = y.load(buf)
    return action_from_dict(dict(loaded))


def test_exe_roundtrip():
    a = ExeAction(file="Run browser.exe", wait=True, delay_ms=200)
    b = _roundtrip(a)
    assert b.file == a.file and b.wait is True and b.delay_ms == 200


def test_exe_minimal():
    a = ExeAction(file="x.exe")
    b = _roundtrip(a)
    assert b.file == "x.exe" and b.wait is None and b.delay_ms is None


def test_play_sound_roundtrip():
    a = PlaySoundAction(name="ok")
    b = _roundtrip(a)
    assert b.name == "ok"


def test_play_sound_rejects_unknown():
    with pytest.raises(SchemaError):
        action_from_dict({"type": "play_sound", "name": "nope"})


def test_system_roundtrip():
    for op in ("volume_mute", "volume_unmute", "exit"):
        a = SystemAction(op=op)
        b = _roundtrip(a)
        assert b.op == op


def test_system_rejects_unknown_op():
    with pytest.raises(SchemaError):
        action_from_dict({"type": "system", "op": "reboot"})


def test_sleep_roundtrip():
    a = SleepAction(ms=1500)
    b = _roundtrip(a)
    assert b.ms == 1500


def test_sleep_rejects_negative():
    with pytest.raises(SchemaError):
        action_from_dict({"type": "sleep", "ms": -1})


def test_shell_roundtrip():
    a = ShellAction(cmd="echo hello", wait=True)
    b = _roundtrip(a)
    assert b.cmd == "echo hello" and b.wait is True


def test_shell_minimal():
    a = ShellAction(cmd="echo x")
    b = _roundtrip(a)
    assert b.wait is None


def test_shell_requires_cmd():
    with pytest.raises(SchemaError):
        action_from_dict({"type": "shell"})


def test_url_roundtrip():
    a = UrlAction(href="https://example.com")
    b = _roundtrip(a)
    assert b.href == "https://example.com"


def test_url_requires_href():
    with pytest.raises(SchemaError):
        action_from_dict({"type": "url"})


def test_keys_sequence_roundtrip():
    a = KeysAction(sequence="ctrl+shift+m")
    b = _roundtrip(a)
    assert b.sequence == "ctrl+shift+m" and b.text is None


def test_keys_text_roundtrip():
    a = KeysAction(text="hello world")
    b = _roundtrip(a)
    assert b.text == "hello world" and b.sequence is None


def test_keys_requires_one_of():
    with pytest.raises(SchemaError):
        action_from_dict({"type": "keys"})


def test_keys_rejects_both():
    with pytest.raises(SchemaError):
        action_from_dict({"type": "keys", "sequence": "ctrl+c", "text": "x"})


def test_multi_roundtrip():
    a = MultiAction(steps=[
        PlaySoundAction(name="ok"),
        ExeAction(file="x.exe", wait=True),
        SleepAction(ms=500),
        UrlAction(href="https://example.com"),
        KeysAction(sequence="ctrl+s"),
        ShellAction(cmd="dir"),
        SystemAction(op="volume_mute"),
    ])
    b = _roundtrip(a)
    assert isinstance(b, MultiAction)
    assert len(b.steps) == 7
    assert isinstance(b.steps[0], PlaySoundAction)
    assert isinstance(b.steps[4], KeysAction)
    assert b.steps[4].sequence == "ctrl+s"


def test_unknown_type_rejected():
    with pytest.raises(SchemaError):
        action_from_dict({"type": "wat"})


def test_command_entry_roundtrip():
    entry = CommandEntry(
        cmd_id="open_site",
        phrases=["открой сайт", "открой пример"],
        action=UrlAction(href="https://example.com"),
    )
    d = entry.to_dict()
    restored = command_from_dict("open_site", d)
    assert restored.cmd_id == "open_site"
    assert restored.phrases == ["открой сайт", "открой пример"]
    assert isinstance(restored.action, UrlAction)
    assert restored.action.href == "https://example.com"


def test_command_requires_phrases():
    with pytest.raises(SchemaError):
        command_from_dict("x", {"phrases": [], "action": {"type": "system", "op": "exit"}})


def test_slugify_russian():
    assert slugify("Открой Браузер") == "otkroy_brauzer"
    assert slugify("hello world") == "hello_world"
    assert slugify("   ") == "cmd"


def _write_fixture(path: Path) -> None:
    path.write_text(
        "existing_cmd:\n"
        "  phrases:\n"
        "    - пример\n"
        "  action: {type: play_sound, name: ok}\n"
        "\n"
        "another:\n"
        "  phrases:\n"
        "    - другой\n"
        "  action: {type: system, op: exit}\n",
        encoding="utf-8",
    )


def test_append_writes_and_creates_backup(tmp_path):
    yaml_path = tmp_path / "commands.yaml"
    _write_fixture(yaml_path)
    original = yaml_path.read_text(encoding="utf-8")
    entry = CommandEntry(
        cmd_id="open_docs",
        phrases=["открой доки", "документация"],
        action=UrlAction(href="https://docs.example.com"),
    )
    append_command(entry, path=yaml_path)
    bak = yaml_path.with_suffix(yaml_path.suffix + ".bak")
    assert bak.exists()
    assert bak.read_text(encoding="utf-8") == original
    data = load_yaml(yaml_path)
    assert "open_docs" in data
    assert "existing_cmd" in data
    assert data["open_docs"]["action"]["href"] == "https://docs.example.com"


def test_append_rejects_duplicate_id(tmp_path):
    yaml_path = tmp_path / "commands.yaml"
    _write_fixture(yaml_path)
    entry = CommandEntry(
        cmd_id="existing_cmd",
        phrases=["дубликат"],
        action=SystemAction(op="exit"),
    )
    with pytest.raises(SchemaError):
        append_command(entry, path=yaml_path)


def test_upsert_overwrites(tmp_path):
    yaml_path = tmp_path / "commands.yaml"
    _write_fixture(yaml_path)
    entry = CommandEntry(
        cmd_id="existing_cmd",
        phrases=["обновлено"],
        action=SystemAction(op="volume_mute"),
    )
    upsert_command(entry, path=yaml_path)
    data = load_yaml(yaml_path)
    assert data["existing_cmd"]["action"]["op"] == "volume_mute"


def test_ruamel_preserves_inline_comments(tmp_path):
    yaml_path = tmp_path / "commands.yaml"
    yaml_path.write_text(
        "# header comment about commands\n"
        "open_browser:\n"
        "  phrases:\n"
        "    - открой браузер\n"
        "  action: {type: exe, file: \"Run browser.exe\"}  # inline note\n",
        encoding="utf-8",
    )
    entry = CommandEntry(
        cmd_id="open_new",
        phrases=["новое"],
        action=UrlAction(href="https://new.example.com"),
    )
    append_command(entry, path=yaml_path)
    text = yaml_path.read_text(encoding="utf-8")
    assert "# header comment about commands" in text
    assert "# inline note" in text
    assert "open_new" in text
