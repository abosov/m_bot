from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "test_data_reset_run.py"
_spec = importlib.util.spec_from_file_location("test_data_reset_run", SCRIPT_PATH)
assert _spec and _spec.loader
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)


class _Args:
    def __init__(self, *, apply: bool, yes: bool, i_know_what_i_am_doing: bool):
        self.apply = apply
        self.yes = yes
        self.i_know_what_i_am_doing = i_know_what_i_am_doing


def test_resolve_registry_prefers_system(tmp_path, monkeypatch):
    repo_root = tmp_path / "backend"
    (repo_root / "config").mkdir(parents=True)
    default_registry = repo_root / "config" / "test_accounts.yaml"
    default_registry.write_text("accounts: []\n", encoding="utf-8")

    system_registry = tmp_path / "etc_test_accounts.yaml"
    system_registry.write_text("accounts: []\n", encoding="utf-8")

    monkeypatch.setattr(module, "SYSTEM_REGISTRY_PATH", system_registry)

    resolved = module.resolve_registry_path(repo_root)
    assert resolved == system_registry


def test_resolve_registry_falls_back_to_default(tmp_path, monkeypatch):
    repo_root = tmp_path / "backend"
    default_registry = repo_root / "config" / "test_accounts.yaml"
    default_registry.parent.mkdir(parents=True)
    default_registry.write_text("accounts: []\n", encoding="utf-8")

    monkeypatch.setattr(module, "SYSTEM_REGISTRY_PATH", tmp_path / "missing_system.yaml")

    resolved = module.resolve_registry_path(repo_root)
    assert resolved == default_registry


def test_apply_guard_requires_explicit_safety_flag():
    with pytest.raises(RuntimeError):
        module.ensure_apply_guards(_Args(apply=True, yes=True, i_know_what_i_am_doing=False))


def test_apply_guard_requires_yes_in_non_interactive(monkeypatch):
    monkeypatch.setattr(module.sys.stdin, "isatty", lambda: False)

    with pytest.raises(RuntimeError):
        module.ensure_apply_guards(_Args(apply=True, yes=False, i_know_what_i_am_doing=True))


def test_apply_guard_non_interactive_with_yes_passes(monkeypatch):
    monkeypatch.setattr(module.sys.stdin, "isatty", lambda: False)

    module.ensure_apply_guards(_Args(apply=True, yes=True, i_know_what_i_am_doing=True))


def test_build_cli_command_uses_absolute_paths(tmp_path):
    repo_root = tmp_path / "backend"
    python_executable = repo_root / ".venv" / "bin" / "python3"
    script_path = repo_root / "scripts" / "test_data_reset.py"
    registry_path = repo_root / "config" / "test_accounts.yaml"

    python_executable.parent.mkdir(parents=True)
    script_path.parent.mkdir(parents=True)
    registry_path.parent.mkdir(parents=True)
    python_executable.write_text("", encoding="utf-8")
    script_path.write_text("", encoding="utf-8")
    registry_path.write_text("accounts: []\n", encoding="utf-8")

    command = module.build_cli_command(
        python_executable=python_executable,
        script_path=script_path,
        passthrough_args=[],
        registry_path=registry_path,
    )

    assert Path(command[0]).is_absolute()
    assert Path(command[1]).is_absolute()
    assert Path(command[0]) == python_executable.resolve()
    assert Path(command[1]) == script_path.resolve()
