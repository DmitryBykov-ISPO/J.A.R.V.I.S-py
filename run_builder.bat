@echo off
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m tools.command_builder
) else (
    python -m tools.command_builder
)
