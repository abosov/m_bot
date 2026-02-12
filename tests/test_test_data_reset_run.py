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
    system_registry = tmp_path / "etc_test_accounts.yaml"
    default_registry = tmp_path / "local_test_accounts.yaml"
    system_registry.write_text("accounts: []\n", encoding="utf-8")
    default_registry.write_text("accounts: []\n", encoding="utf-8")

    monkeypatch.setattr(module, "SYSTEM_REGISTRY_PATH", system_registry)
    monkeypatch.setattr(module, "DEFAULT_REGISTRY_PATH", default_registry)

    resolved = module.resolve_registry_path(None)
    assert resolved == system_registry


def test_resolve_registry_falls_back_to_default(tmp_path, monkeypatch):
    system_registry = tmp_path / "missing_system.yaml"
    default_registry = tmp_path / "local_test_accounts.yaml"
    default_registry.write_text("accounts: []\n", encoding="utf-8")

    monkeypatch.setattr(module, "SYSTEM_REGISTRY_PATH", system_registry)
    monkeypatch.setattr(module, "DEFAULT_REGISTRY_PATH", default_registry)

    resolved = module.resolve_registry_path(None)
    assert resolved == default_registry


def test_apply_guard_requires_explicit_safety_flag():
    with pytest.raises(RuntimeError):
        module.ensure_apply_guards(_Args(apply=True, yes=True, i_know_what_i_am_doing=False))


def test_apply_guard_requires_yes_in_non_interactive(monkeypatch):
    monkeypatch.setattr(module.sys.stdin, "isatty", lambda: False)

    with pytest.raises(RuntimeError):
        module.ensure_apply_guards(_Args(apply=True, yes=False, i_know_what_i_am_doing=True))
